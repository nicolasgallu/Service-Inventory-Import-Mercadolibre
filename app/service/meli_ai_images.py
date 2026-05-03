import os
import io
import json
import re
import requests
import google.auth
from PIL import Image
from google.cloud import secretmanager
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import credentials
from google.auth.transport.requests import Request

from app.settings.config import PROJECT_ID
from app.service.database import get_item_data
from app.service.secrets import meli_secrets
from app.utils.logger import logger

# --- CONFIGURATION ---
SECRET_ID = "secrets--guiaslocales-api"
SCOPES_DRIVE = ['https://www.googleapis.com/auth/drive.file']

def extract_id_from_url(url):
    """
    Extracts the Google Drive folder ID from a URL.
    Handles standard /folders/ID format and ?id=ID format.
    """
    match = re.search(r"(?<=folders/|id=)([a-zA-Z0-9-_]{25,})", url)
    return match.group(0) if match else None

def get_drive_creds_from_secret():
    """
    Uses ADC to access Secret Manager and returns refreshed OAuth credentials.
    """
    adc_creds, _ = google.auth.default()
    client = secretmanager.SecretManagerServiceClient(credentials=adc_creds)
    
    secret_path = f"projects/{PROJECT_ID}/secrets/{SECRET_ID}/versions/latest"
    
    response = client.access_secret_version(request={"name": secret_path})
    creds_dict = json.loads(response.payload.data.decode("UTF-8"))
    
    drive_creds = credentials.Credentials.from_authorized_user_info(creds_dict, SCOPES_DRIVE)
    
    if not drive_creds or not drive_creds.valid:
        if drive_creds and drive_creds.expired and drive_creds.refresh_token:
            logger.info("🔄 Refreshing Drive Access Token...")
            drive_creds.refresh(Request())
            
            new_creds_dict = json.loads(drive_creds.to_json())
            parent = f"projects/{PROJECT_ID}/secrets/{SECRET_ID}"
            payload = json.dumps(new_creds_dict).encode("UTF-8")
            client.add_secret_version(request={"parent": parent, "payload": {"data": payload}})
            logger.info("✅ Secret Manager updated with fresh token.")
            
    return drive_creds

def mvp_meli_pictures(item_id):
    """
    Entry point for the Cloud Function.
    Now uses a direct folder URL instead of searching by name.
    """
    try:
        # 1. Get Folder ID directly from the provided URL
        meli_id = get_item_data(item_id).get('meli_id')
        folder_url = get_item_data(item_id).get('drive_url')        
        token = meli_secrets()

        folder_id = extract_id_from_url(folder_url)
        if not folder_id:
            logger.error(f"Could not extract ID from URL: {folder_url}")
            return "Invalid Folder URL", 400

        # 2. Get Drive Service
        drive_creds = get_drive_creds_from_secret()
        drive_service = build('drive', 'v3', credentials=drive_creds)

        # 4. Get MeLi Images
        url = f"https://api.mercadolibre.com/items/{meli_id}"
        headers = {'Authorization' : f'Bearer {token}'}
        resp = requests.get(url, headers=headers).json()
        pictures = resp.get('pictures', [])

        if not pictures:
            logger.info(f"No images found for MeLi item {meli_id}")
            return "No images found", 200

        # 5. Process and Upload Images
        for idx, pic in enumerate(pictures):
            img_url = pic.get('secure_url')
            img_resp = requests.get(img_url)
            
            if img_resp.status_code == 200:
                with Image.open(io.BytesIO(img_resp.content)) as img:
                    # Convert to PNG in memory
                    png_buffer = io.BytesIO()
                    img.save(png_buffer, format='PNG')
                    png_buffer.seek(0)

                    file_meta = {
                        'name': f"{item_id}_{idx}.png", 
                        'parents': [folder_id]
                    }
                    media = MediaIoBaseUpload(png_buffer, mimetype='image/png')
                    
                    drive_service.files().create(
                        body=file_meta, 
                        media_body=media,
                        supportsAllDrives=True
                    ).execute()
                    
                    logger.info(f"Uploaded image {idx} to Drive folder {folder_id}")

        return "Success", 200

    except Exception as e:
        logger.error(f"Error in mvp_meli_pictures: {str(e)}")
        return f"Internal Error: {str(e)}", 500