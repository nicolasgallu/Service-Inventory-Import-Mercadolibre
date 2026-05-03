import os
import io
import json
import requests
from PIL import Image
from google.cloud import secretmanager
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import credentials
from google.auth.transport.requests import Request
from app.settings.config import PROJECT_ID
import google.auth # This handles ADC
from app.service.database import get_item_data
from app.service.secrets import meli_secrets
from app.utils.logger import logger


# --- CONFIGURATION ---
# In Cloud Functions, PROJECT_ID is usually available as an env var
SECRET_ID = "secrets--guiaslocales-api"

DRIVE_PARENT_ID = '1dd2P6OkaFgvkah-sBr_sjagAnCk31n-v'
SCOPES_DRIVE = ['https://www.googleapis.com/auth/drive.file']

def get_drive_creds_from_secret():
    """
    Uses ADC to access Secret Manager and returns refreshed OAuth credentials.
    """
    # 1. Initialize Secret Manager using ADC
    # google.auth.default() automatically finds the service account credentials
    adc_creds, _ = google.auth.default()
    client = secretmanager.SecretManagerServiceClient(credentials=adc_creds)
    
    secret_path = f"projects/{PROJECT_ID}/secrets/{SECRET_ID}/versions/latest"
    
    # 2. Get the OAuth Dictionary
    response = client.access_secret_version(request={"name": secret_path})
    creds_dict = json.loads(response.payload.data.decode("UTF-8"))
    
    # 3. Create Drive Credentials object
    drive_creds = credentials.Credentials.from_authorized_user_info(creds_dict, SCOPES_DRIVE)
    
    # 4. Refresh if needed
    if not drive_creds or not drive_creds.valid:
        if drive_creds and drive_creds.expired and drive_creds.refresh_token:
            logger.info("🔄 Refreshing Drive Access Token...")
            drive_creds.refresh(Request())
            
            # Update the secret so the next execution has a fresh token
            new_creds_dict = json.loads(drive_creds.to_json())
            parent = f"projects/{PROJECT_ID}/secrets/{SECRET_ID}"
            payload = json.dumps(new_creds_dict).encode("UTF-8")
            client.add_secret_version(request={"parent": parent, "payload": {"data": payload}})
            logger.info("✅ Secret Manager updated with fresh token.")
            
    return drive_creds

def mvp_meli_pictures(item_id):
    """
    Entry point for the Cloud Function.
    """
    try:
        # Get Drive Service
        drive_creds = get_drive_creds_from_secret()
        drive_service = build('drive', 'v3', credentials=drive_creds)

        # MeLi Info (This could be passed via 'event' data)
        meli_id = get_item_data(item_id).get('meli_id')
        token = meli_secrets()
        
        # 1. Get MeLi Images
        url = f"https://api.mercadolibre.com/items/{meli_id}"
        headers = {'Authorization' : f'Bearer {token}'}
        resp = requests.get(url, headers=headers).json()
        pictures = resp.get('pictures', [])

        if not pictures:
            return "No images found", 200

        # 2. Setup Drive Folder
        query = f"name = '{item_id}' and '{DRIVE_PARENT_ID}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        res = drive_service.files().list(q=query, fields="files(id)").execute()
        items = res.get('files', [])
        logger.info("now returning items info")
        logger.info(items)
        
        folder_id = items[0]['id']

        # 3. Process Images
        for idx, pic in enumerate(pictures):
            img_url = pic.get('secure_url')
            img_resp = requests.get(img_url)
            
            if img_resp.status_code == 200:
                # Open with PIL (handles webp/jpg/png)
                with Image.open(io.BytesIO(img_resp.content)) as img:
                    # Convert to PNG in memory
                    png_buffer = io.BytesIO()
                    img.save(png_buffer, format='PNG')
                    png_buffer.seek(0)

                    file_meta = {'name': f"{item_id}_{idx}.png", 'parents': [folder_id]}
                    media = MediaIoBaseUpload(png_buffer, mimetype='image/png')
                    drive_service.files().create(body=file_meta, media_body=media,supportsAllDrives=True).execute()
                    logger.info(f"Uploaded {idx}")

        return "Success", 200

    except Exception as e:
        logger.info(f"Error: {str(e)}")
        return f"Internal Error: {str(e)}", 500
    

