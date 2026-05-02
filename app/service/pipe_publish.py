from app.service.secrets import meli_secrets
from app.service.database import get_item_data
from app.service.ai_completation import ai_call_prepublish
from app.service.google_pictures import process_images_storage
from app.service.meli_api import publish_item, update_item, pause_item, delete_item
from app.service.tienda_nube_api import tienda_nube_publish_item, tienda_nube_update_item, tienda_nube_delete_item
from app.utils.logger import logger
from app.service.meli_ai_images import mvp_meli_pictures

def pipeline_publish(response):
    """
    """
    event_type = response['event_type']
    item_id = response['item_id']
    
    if response['site'] == 'tienda-nube':
        logger.info("TiendaNube Product Notification")        
        if event_type == "delete":
            tienda_nube_delete_item(item_id)
        elif event_type == "publish":
            tienda_nube_publish_item(item_id)
        elif event_type == "update":
            tienda_nube_update_item(item_id)
        return

    else:

        try:
            logger.info("Meli Product Notification")
            item_data = get_item_data(item_id)
            token = meli_secrets()

            if event_type == "meli_pictures":
                logger.info(response.get('data').get('field'))
                mvp_meli_pictures(item_id)
                tienda_nube_update_item(item_id)

            if event_type == "pre-publish":
                logger.info(response.get('data').get('field'))
                ai_call_prepublish(response, item_data)

            elif event_type == "delete":
                delete_item(item_data, token)

            elif event_type == "pause":
                pause_item(item_data, token)

            elif event_type in ["publish", "update"]:
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