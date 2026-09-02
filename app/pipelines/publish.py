import asyncio
from app.integrations.core.ai_completation import ai_call_prepublish
from app.integrations.mercadolibre.grid_size import create_template, create_grid
from app.integrations.mercadolibre.product_handler import prepublish, publish as meli_publish, update as meli_update, pause as meli_pause, delete as meli_delete
from app.integrations.tiendanube.product_handler import create_categories, publish as tnube_publish, update as tnube_update, delete as tnube_delete
from app.integrations.mercadolibre.ai_images import mvp_meli_pictures
from app.utils.logger import logger

def pipeline_publish(payload):

    target = payload.get('target')
    event_type = payload.get('event_type')
    logger.info(f"Event: {event_type} | Target: {target}")
    
    if event_type == 'prepublish':
        asyncio.run(ai_call_prepublish(payload))
        if target == "mercadolibre":
            prepublish(payload)
        elif target == "tiendanube":
            create_categories(payload)

    elif event_type == 'publish':
        if target == "mercadolibre":
            meli_publish(payload)
        elif target == "tiendanube":
            tnube_publish(payload)

    elif event_type == 'update':
        if target == "mercadolibre":
            meli_update(payload)
        elif target == "tiendanube":
            tnube_update(payload)

    elif event_type == 'pause':
        if target == "mercadolibre":
            meli_pause(payload)

    elif event_type == 'delete':
        if target == "mercadolibre":
            meli_delete(payload)
        elif target == "tiendanube":
            tnube_delete(payload)

    elif event_type == 'meli_pictures':
        mvp_meli_pictures(payload)

    elif event_type == "create_template":
        create_template(payload)
        
    elif event_type == "create_size_grid":
        create_grid(payload)
                
    else:
        return

