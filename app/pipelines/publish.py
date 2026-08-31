import asyncio
from app.service.ai_completation import ai_call_prepublish
from app.integrations.mercadolibre.grid_size import create_template, create_grid
from app.integrations.mercadolibre.meli_api import prepublish_product, publish_item, update_item, pause_item, delete_item
from app.integrations.tiendanube.product_handler import create_categories, tienda_nube_publish_item, tienda_nube_update_item, tienda_nube_delete_item
from app.integrations.mercadolibre.ai_images import mvp_meli_pictures
from app.utils.logger import logger

def pipeline_publish(payload):

    product_id = payload.get('product_id')
    event_type = payload.get('event_type')
    site = payload.get('site')

    logger.info(f"Event Received: {event_type}")
    if event_type == 'pre-publish':
        asyncio.run(ai_call_prepublish(payload))
        prepublish_product(payload)

    
#    elif 'site' in payload:
#        if payload['site'] == 'tienda-nube':
#            logger.info("TiendaNube Product Notification")        
#            if event_type == "delete":
#                tienda_nube_delete_item(item_id)
#            elif event_type == "publish":
#                tienda_nube_publish_item(item_id)
#            elif event_type == "update":
#                tienda_nube_update_item(item_id)
#            elif event_type == "create_category":
#                name = payload.get('name')
#                create_categories(name)
#                

    #if event_type == "meli_pictures":
    #    mvp_meli_pictures(item_id)
    #    tienda_nube_update_item(item_id)

    if event_type == "publish": 
        publish_item(payload)
    elif event_type == "update":
        update_item(payload)
    elif event_type == "pause":
        pause_item(payload)
    elif event_type == "delete":
        delete_item(payload)

    #elif event_type == "create_template":
    #    create_template(item_id)
    #elif event_type == "create_size_grid":
    #    create_grid(item_id)
#    return