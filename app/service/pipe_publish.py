from app.service.secrets import meli_secrets
from app.service.database import get_item_data
from app.service.ai_completation import ai_call_prepublish
from app.service.google_pictures import process_images_storage
from app.service.meli_api import publish_item, update_item, pause_item
from app.utils.logger import logger

def pipeline_publish(response):
    """
    """
    try:
        event_type = response['event_type']
        item_id = response['item_id']
        item_data = get_item_data(item_id)
        logger.info(f"Background Processing Event: {event_type} for ID: {item_id}")
        
        if event_type == "pre-publish":
            logger.info(response.get('data').get('field'))
            ai_call_prepublish(response, item_data)

        elif event_type == "pause":
            token = meli_secrets()
            pause_item(item_data, token)

        elif event_type in ["publish", "update"]:
            token = meli_secrets()
            public_images = process_images_storage(item_id)
            if public_images == []:
                logger.info("Public Images in Drive not founded, using image from Bitcram..")
                public_images = [{'source': item_data["product_image_b_format_url"]}]

            if event_type == "publish":
                publish_item(item_data, public_images, token)
            
            elif event_type == "update":
                update_item(item_data, public_images, token)

    except Exception as error:
        logger.error(f"Error in background task: {str(error)}")