import threading # <--- Importante
from app.service.secrets import meli_secrets
from app.service.database import get_item_data
from app.service.google_pictures import process_images_storage
from app.service.meli_api import publish_item, update_item, pause_item
from app.utils.logger import logger
from app.settings.config import SECRET_GUIAS
from flask import Blueprint, request, Response, jsonify

# BLUEPRINT CREATION
meli_publish = Blueprint("wh_publish", __name__, url_prefix="/webhooks/publications")

def process_notification(response):
    """
    Función que envuelve toda tu lógica original para ser ejecutada 
    en un hilo separado (background).
    """
    try:
        item_id = response['item_id']
        event_type = response['event_type']
        item_data = get_item_data(item_id)
        logger.info(f"Background Processing Event: {event_type} for ID: {item_id}")
        token = meli_secrets()

        if event_type == "pause":
            pause_item(item_data, token)

        elif event_type in ["publish", "update"]:
            
            public_images = process_images_storage(item_id)
            if public_images == []:
                logger.info("Public Images in Drive not founded, using image from Bitcram..")
                public_images = [{'source': item_data["product_image_b_format_url"]}]
            
            if item_data['product_name_meli']:
                item_data['product_name'] = item_data['product_name_meli'] ##sobreescribo el valor en product name para no tener que sumar complejidad.


            if event_type == "publish":
                publish_item(item_data, public_images, token)
            
            elif event_type == "update":
                update_item(item_data, public_images, token)

    except Exception as error:
        logger.error(f"Error in background task: {str(error)}")


@meli_publish.route("", methods=["POST"], strict_slashes=False)
def main():
    response = request.json
    
    # 1. Validación rápida (esto es lo único que bloquea al cliente)
    if not response or 'secret' not in response:
        return Response(status=400)

    if SECRET_GUIAS != response['secret']:
        return Response(status=401)
    
    logger.info("Receving notification from App Import - Dispatching thread")

    # 2. Creamos y lanzamos el hilo con la lógica pesada
    # Pasamos una copia de los datos para evitar problemas de contexto
    thread = threading.Thread(target=process_notification, args=(response,))
    thread.start()

    # 3. Respondemos de inmediato
    # 202 significa "Accepted" (aceptado para procesamiento, pero no completado aún)
    return jsonify({"status": "accepted", "message": "Task dispatched to background"}), 202