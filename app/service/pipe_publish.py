from app.service.secrets import meli_secrets
from app.service.ai_completation import ai_call_prepublish
from app.service.meli_api import prepublish_product, publish_item, update_item, pause_item, delete_item
from app.service.tienda_nube_api import create_categories, tienda_nube_publish_item, tienda_nube_update_item, tienda_nube_delete_item
from app.utils.logger import logger
from app.service.meli_ai_images import mvp_meli_pictures

def pipeline_publish(response):
    """"""
    try:
        item_id = response.get('item_id')
        event_type = response.get('event_type')
        if event_type == 'pre-publish':
            logger.info("Pre-Publish Notification.")
            data = response.get('data')
            ai_call_prepublish(data, item_id)
            token = meli_secrets()
            prepublish_product(item_id, token)

        elif 'site' in response:
            if response['site'] == 'tienda-nube':
                logger.info("TiendaNube Product Notification")        
                if event_type == "delete":
                    tienda_nube_delete_item(item_id)
                elif event_type == "publish":
                    tienda_nube_publish_item(item_id)
                elif event_type == "update":
                    tienda_nube_update_item(item_id)
                elif event_type == "create_category":
                    name = response.get('name')
                    create_categories(name)
                    
        else:
            logger.info("Meli Product Notification")
            token = meli_secrets()
            if event_type == "meli_pictures":
                logger.info("executing mvp meli pictures job")
                mvp_meli_pictures(item_id)
                tienda_nube_update_item(item_id)
            elif event_type == "publish": 
                publish_item(item_id, token)
            elif event_type == "update":
                update_item(item_id, token)
            elif event_type == "pause":
                pause_item(item_id, token)
            elif event_type == "delete":
                delete_item(item_id, token)
        return
    
    except Exception:
        logger.exception(Exception)
        raise
                