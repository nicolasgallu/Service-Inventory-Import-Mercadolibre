from app.utils.logger import logger
from app.service.secrets import meli_secrets, tienda_nube_secrets
from app.service.database import get_order, insert_order, get_bitcram_data, get_tienda_nube_id
from app.service.post_bitcram import sell_workflow
from app.service.notifications import enviar_mensaje_whapi
from app.settings.config import PHONE_INTERNAL, PHONE_CUSTOMER, TOKEN_WHAPI
import requests
import json

def pipeline_selling(order_id, platform):
    """"""

    logger.info(f"processing order {order_id} from {platform}")

    if get_order(order_id, platform):
        logger.info(f"Order: {order_id} already processed, skipping.")
        return
    
    message= f'Nueva Orden Generada desde {platform}\n {order_id}' 
    enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_CUSTOMER, message)

    try:
        if platform == 'mercadolibre':

            token = meli_secrets()
            url = f"https://api.mercadolibre.com/orders/{order_id}"
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(url, headers=headers)

            if response.status_code < 300:
                logger.info("Order Information correctly pulled from Mercadolibre")
                order_data = response.json()
                order_id = order_data.get('id')
                created_at = order_data.get('date_created')
                order_items = order_data.get('order_items', [])
                order = {'id':order_id,'data': json.dumps(order_items) ,'created_at': created_at}
                logger.info("Order Dict Created.")

                for item_info in order_items:
                    meli_id = item_info.get('item', {}).get('id')
                    quantity = item_info.get('quantity')
                    unit_price = item_info.get('unit_price')
                    data = get_bitcram_data(meli_id)
                    id = data.get('id')
                    insert_order(order, platform)
                    sell_workflow(id, quantity, unit_price)

            else:
                logger.error(f"Error processing the order: {response.json()}")
                message = f"fallo en la orden de mercadolibre: {order_id}\n {response.json()}"
                enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, message)
                return


        elif platform == 'tienda_nube':

            token, user_id = tienda_nube_secrets()
            url = f"https://api.tiendanube.com/v1/{user_id}/orders/{order_id}"
            headers = {
                'Authentication': f'bearer {token}',
                'Content-Type': 'application/json'}
            response = requests.get(url=url, headers=headers)

            if response.status_code < 300:
                logger.info("Order Information correctly pulled from TiendaNube")
                order_data = response.json()
                order_id = order_data.get('id')
                created_at = order_data.get('created_at')
                order_info = order_data
                product_id = order_data.get('products')[0].get('product_id')
                price = order_data.get('products')[0].get('price')
                quantity = order_data.get('products')[0].get('quantity')
                order = {'id':order_id,'data': json.dumps(order_info) ,'created_at': created_at}
                logger.info("Order Dict Created.")

                data = get_tienda_nube_id(product_id)
                id = data.get('id')
                insert_order(order, platform)
                sell_workflow(id, quantity, price)

            else:
                logger.error(f"Error processing the order: {response.json()}")
                message = f"fallo en la orden de tiendanube: {order_id}\n {response.json()}"
                enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, message)
                return
        return

        

    except Exception as e:
        logger.error(f"Error processing the order: {e}")
        message = f"fallo en la orden de {platform}: {order_id}"
        enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, message)
        return


