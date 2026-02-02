import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from google.cloud import storage
from google.oauth2 import service_account
from app.utils.logger import logger

# === CONFIGURACIÓN ===
SERVICE_ACCOUNT_FILE = 'service_account.json'
ID_CARPETA_MADRE = '1dd2P6OkaFgvkah-sBr_sjagAnCk31n-v'
BUCKET_NAME = 'bucket_import_fotos'


def get_services():
    """Inicializa los servicios de Drive y Storage."""
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
    
    drive_service = build('drive', 'v3', credentials=creds)
    storage_client = storage.Client(credentials=creds)
    bucket_client = storage_client.bucket(BUCKET_NAME)
    
    return drive_service, bucket_client


def process_images_storage(item_id):
    """
    Busca una carpeta por item_id, descarga las últimas 5 fotos 
    y las sube a un bucket de GCS como archivos .png públicos.
    """
    drive_service, bucket_client = get_services()

    # 1. Buscar la carpeta específica del ítem dentro de la carpeta madre
    folder_query = (
        f"name = '{item_id}' "
        f"and '{ID_CARPETA_MADRE}' in parents "
        f"and mimeType = 'application/vnd.google-apps.folder' "
        f"and trashed = false"
    )
    
    folders = drive_service.files().list(q=folder_query, fields="files(id)").execute().get('files', [])

    if not folders:
        logger.error(f"Error: folder: '{item_id}' not found in parent folder.")
        return None
    
    folder_id = folders[0]['id']

    # 2. Listar archivos dentro de la carpeta (ordenar por los últimos creados)
    # Filtramos para intentar traer solo imágenes
    file_query = f"'{folder_id}' in parents and mimeType contains 'image/' and trashed = false"
    results = drive_service.files().list(
        q=file_query, 
        orderBy="createdTime desc", 
        fields="files(id, name, mimeType)"
    ).execute().get('files', [])

    if not results:
        logger.info(f"Folder: '{item_id}' is empty.")
        return None

    # Tomamos solo los últimos 5
    last_5_files = results[:5]
    public_images = []

    logger.info(f"Processing {len(last_5_files)} images from item: {item_id}...")

    # 3. Descarga y Carga (Stream)
    for index, file in enumerate(last_5_files):
        file_id = file['id']
        # Definimos el nombre de destino en el Bucket (sobrescribe si ya existe)
        blob_name = f"{item_id}/foto_{index + 1}.png"
        blob = bucket_client.blob(blob_name)

        # Descarga de Drive a Buffer de memoria
        request = drive_service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        
        done = False
        while not done:
            _, done = downloader.next_chunk()
        
        file_stream.seek(0)

        # Subida a GCS
        blob.upload_from_file(file_stream, content_type='image/png')
        
        # Ya no usamos blob.make_public() porque el bucket ya es público por IAM
        # Solo obtenemos la URL
        public_url = f"https://storage.googleapis.com/{BUCKET_NAME}/{blob_name}"
        public_images.append({'source':public_url})
        
        logger.info("Finish images loaded in bucket")
    # 4. Resultado final
    return public_images




