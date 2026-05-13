from app.service.secrets import meli_secrets
from app.service.ai_completation import ai_call_prepublish
#from app.service.google_pictures import process_images_storage
from app.service.meli_api import publish_item, update_item, pause_item, delete_item, get_data_for_meli, prepublish_product
from app.service.tienda_nube_api import tienda_nube_publish_item, tienda_nube_update_item, tienda_nube_delete_item
from app.utils.logger import logger
#from app.service.meli_ai_images import mvp_meli_pictures

def pipeline_publish(response):
    """
    """
    item_id = response.get('item_id')
    event_type = response.get('event_type')
    data = response.get('data')

    if event_type == 'pre-publish':
        logger.info("Pre-Publish Notification.")
        item_data = get_data_for_meli(item_id)
        ai_call_prepublish(data, item_data)
        token = meli_secrets()
        prepublish_product(item_data, token)
        return

    #elif 'site' in response:
    #    if response['site'] == 'tienda-nube':
    #        logger.info("TiendaNube Product Notification")        
    #        if event_type == "delete":
    #            tienda_nube_delete_item(item_id)
    #        elif event_type == "publish":
    #            tienda_nube_publish_item(item_id)
    #        elif event_type == "update":
    #            tienda_nube_update_item(item_id)
    #        return


    else:
        logger.info("Meli Product Notification")
        item_data = get_data_for_meli(item_id)
        token = meli_secrets()
        #elif event_type == "meli_pictures":
        #    logger.info("executing mvp meli pictures job")
        #    mvp_meli_pictures(item_id)
        #    tienda_nube_update_item(item_id)

        if event_type in ["publish", "update"]:
            #public_images = process_images_storage(item_id)
            public_images = []
            if public_images == []:
                logger.info("Without images in Folder, using image from Bitcram.")
                public_images = [{'source': item_data["product_image_b_format_url"]}]
            if event_type == "publish": 
                publish_item(item_data, public_images, token)
            elif event_type == "update":
                update_item(item_id, item_data, public_images, token)

        elif event_type == "pause":
            pause_item(item_data, token)

        elif event_type == "delete":
            delete_item(item_data, token)