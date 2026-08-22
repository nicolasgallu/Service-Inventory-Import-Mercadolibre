import io
import time
from datetime import datetime
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError
from google.cloud import storage
import google.auth
from googleapiclient.discovery import build
from app.utils.logger import logger
from app.settings.config import ID_CARPETA_MADRE, BUCKET_NAME
import httplib2

def get_services():
    """
    Inicializa los servicios de Drive y Storage usando Application Default Credentials (ADC).
    En GCP, esto toma automáticamente los permisos de la Service Account asociada.
    """
    http = httplib2.Http(timeout=60)
    try:
        creds, project = google.auth.default(
            scopes=[
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/cloud-platform'
            ]
        )
        drive_service = build('drive', 'v3', credentials=creds, http=http)
        storage_client = storage.Client(credentials=creds)
        bucket_client = storage_client.bucket(BUCKET_NAME)
        return drive_service, bucket_client
    except Exception as e:
        logger.error(f"Error al inicializar servicios de GCP: {e}")
        raise


def drive_execute(request, retries=3):
    for attempt in range(retries):
        try:
            return request.execute()
        except (BrokenPipeError, ConnectionResetError, TimeoutError) as e:
            if attempt == retries - 1:
                raise

            wait = 2 ** attempt
            logger.warning(
                "Google Drive connection error. Retrying in %s seconds "
                "(attempt %s/%s): %s",
                wait, attempt + 1, retries, e
            )
            time.sleep(wait)
        except HttpError as e:
            if e.resp.status not in (429, 500, 502, 503, 504):
                raise
            if attempt == retries - 1:
                raise

            wait = 2 ** attempt
            logger.warning(
                "Google Drive HTTP %s. Retrying in %s seconds "
                "(attempt %s/%s)",
                e.resp.status, wait, attempt + 1, retries
            )
            time.sleep(wait)


def process_images_storage(item_id):
    """
    Busca una carpeta por item_id, descarga las últimas 5 fotos
    y las sube a un bucket de GCS como archivos .png públicos.
    """
    drive_service, bucket_client = get_services()

    folder_query = (
        f"name = '{item_id}' "
        f"and '{ID_CARPETA_MADRE}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )

    folders = drive_execute(drive_service.files().list(q=folder_query, fields="files(id)")).get('files', [])

    if not folders:
        logger.warning(f"Error: folder: '{item_id}' not found in parent folder.")
        return []

    folder_id = folders[0]['id']
    file_query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"

    results = drive_execute(
        drive_service.files().list(
            q=file_query,
            orderBy="createdTime desc",
            fields="files(id, name, mimeType)"
        )
    ).get('files', [])

    if not results:
        logger.info(f"Folder: '{item_id}' is empty.")
        return []

    last_5_files = results[:5]
    public_images = []

    logger.info(f"Processing {len(last_5_files)} images from item: {item_id}...")

    for blob in bucket_client.list_blobs(prefix=f"{item_id}/"):
        blob.delete()

    for index, file in enumerate(last_5_files):
        file_id = file['id']
        blob_name = f"{item_id}/foto_{datetime.now().isoformat()}_{index + 1}.png"
        blob = bucket_client.blob(blob_name)
        request = drive_service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        
        done = False
        while not done:
            _, done = downloader.next_chunk()

        file_stream.seek(0)
        blob.upload_from_file(file_stream, content_type='image/png')
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
        public_images.append({'source': public_url})
        logger.info("Finish images loaded in bucket")

    return public_images