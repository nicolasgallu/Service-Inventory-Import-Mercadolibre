from app.service.secrets import meli_secrets
from app.service.database import get_item_data, get_method
from app.service.ai_completation import ai_call_prepublish
#from app.service.google_pictures import process_images_storage
from app.service.meli_api import publish_item, update_item, pause_item, delete_item
from app.service.tienda_nube_api import tienda_nube_publish_item, tienda_nube_update_item, tienda_nube_delete_item
from app.utils.logger import logger
#from app.service.meli_ai_images import mvp_meli_pictures

def pipeline_publish(response):
    """
    """
    event_type = response['event_type']
    item_id = response['item_id']

    #if event_type == 'pre-publish':
    #    logger.info("Processing Pre-Publish Event")
    #    item_data = get_item_data(item_id)
    #    ai_call_prepublish(response, item_data)
    #    return
#
#
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
#


    if 'foo' == 'dummy':
        return

    else:

        try:
            logger.info("Meli Product Notification")
            query = {
                'q_columns': [
                    'a.id',
                    'a.price',
                    'a.product_code',
                    'a.product_name',
                    'a.product_image_b_format_url',
                    'a.stock',
                    'a.cost',
                    'a.product_name_meli',
                    'a.description',
                    'a.brand',
                    'a.meli_id',
                    'a.drive_url',
                    'a.price_mercadolibre',
                    'a.dimentions',
                    'a.model',
                    'a.listing_type_id',
                    'a.free_shipping',
                    'a.mode_shipping',
                    'b.volume_capacity'
                ],
                'q_from':'FROM guias_locales_testing.product_catalog_sync as a',
                'q_join':'LEFT JOIN guias_locales_testing.attributes as b on b.item_id = a.id',
                'q_where': f'WHERE a.id = {item_id}',
                'q_limit':'LIMIT 1'
            }
            item_data = get_method(query)
            token = meli_secrets()

            #if event_type == "meli_pictures":
            #    logger.info("executing mvp meli pictures job")
            #    mvp_meli_pictures(item_id)
            #    tienda_nube_update_item(item_id)

            if 'foo' == 'dummy':
                return

            elif event_type == "delete":
                delete_item(item_data, token)

            elif event_type == "pause":
                pause_item(item_data, token)

            elif event_type in ["publish", "update"]:
                #public_images = process_images_storage(item_id)
                public_images = []
                if public_images == []:
                    logger.info("Public Images in Drive not founded, using image from Bitcram..")
                    public_images = [{'source': item_data["product_image_b_format_url"]}]

                if event_type == "publish":
                    publish_item(item_data, public_images, token)

                elif event_type == "update":
                    update_item(item_data, public_images, token)

        except Exception as error:
            logger.error(f"Error in background task: {str(error)}")