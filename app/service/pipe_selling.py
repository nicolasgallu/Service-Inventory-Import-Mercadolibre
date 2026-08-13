from app.utils.logger import logger
from app.service.secrets import meli_secrets, tienda_nube_secrets
from app.service.database import get_order, insert_order, get_method, get_tienda_nube_id, upsert_method
from app.service.post_bitcram import sell_workflow
from app.service.notifications import enviar_mensaje_whapi
from app.settings.config import (
    PHONE_INTERNAL, 
    PHONE_CUSTOMER, 
    TOKEN_WHAPI, 
    SCHEMA_INVENTORY, 
    SCHEMA_MERCADOLIBRE
)
import requests
import json

PRODUCTS_TABLE = 'product_catalog_sync'
PROD_STATUS_TABLE_MELI = 'product_status'
ORDERS_TABLE_MELI = 'orders'

def pipeline_selling(order_id, platform):
    """"""
    
    logger.info(f"processing order {order_id} from {platform}")
    
    try:
        if platform == 'mercadolibre':
            query_meli = {
                'q_columns': ['a.id','a.status'],
                'q_from':f'FROM {SCHEMA_MERCADOLIBRE}.{ORDERS_TABLE_MELI} as a',
                'q_where': f"WHERE a.id = '{order_id}'",
                'q_limit':'LIMIT 1'}
            token = meli_secrets()
            url = f"https://api.mercadolibre.com/orders/{order_id}"
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(url, headers=headers)

            if response.status_code < 300:
                logger.info("Order Information correctly pulled from Mercadolibre")
                order_data = response.json()
                order_in_db = get_method(query_meli)[0] if get_method(query_meli) else {}
                DEVOLUTION_MULTIPLIER = 1
                IS_NEW_ORDER = True

                if order_in_db.get('id'):
                    IS_NEW_ORDER = False
                    previous_status = order_in_db.get("status")

                order_status = order_data["status"]

                if order_status not in ["cancelled", "paid"]:
                    logger.info(f"Order is neither paid or cancelled: {order_status}")
                    return

                elif order_status == "cancelled":
                    logger.info("Order is cancelled. Starting cancellation/idempotency check.")
                    if IS_NEW_ORDER:
                        logger.info("Order does not exist in the database. Skipping cancellation.")
                        return
                    logger.info(f"Order exists in the database. Previous status: {previous_status}")
                    if previous_status == order_status:
                        logger.info("Cancellation already processed. Skipping.")
                        return
                    logger.info(f"New cancellation detected: {previous_status} -> {order_status}. Processing.")
                    DEVOLUTION_MULTIPLIER = -1

                elif order_status == "paid":
                    logger.info("Order status is paid.")
                    if IS_NEW_ORDER:
                        logger.info("Order does not exist in the database. Processing.")
                    else:
                        logger.info(f"Order exists in the database. Previous status: {previous_status}")
                        if previous_status == order_status:
                            logger.info("Paid already processed. Skipping.")
                            return
                        logger.info(f"New paid detected: {previous_status} -> {order_status}. Processing.")

                message= f'Orden Generada desde: {platform}\norder_id: {order_id}\nstatus: {order_status}' 
                enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_CUSTOMER, message)
                enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, message)

                order_id = order_data.get('id')
                created_at = order_data.get('date_created')
                order_items = order_data.get('order_items', [])
                pack_id = order_data.get('pack_id', None)
                order = {'id':{'value': order_id, 'type': 'char'},
                         'data':  {'value': json.dumps(order_items), 'type': 'json'}, 
                         'pack_id':{'value': pack_id, 'type': 'char'}, 
                         'created_at': {'value': created_at, 'type': 'datetime'},
                         'status': {'value': order_status, 'type': 'char'},
                }
                logger.info("Order Dict Created. saving order in DB.")
                upsert_method(order, SCHEMA_MERCADOLIBRE, ORDERS_TABLE_MELI)
                
                for item_info in order_items:
                    meli_id = item_info.get('item', {}).get('id')
                    url = f"https://api.mercadolibre.com/items/{meli_id}?include_attributes=all"
                    response = requests.get(url, headers=headers).json()

                    sku = response.get("seller_sku")
                    gtin = None
                    for attr in response.get("attributes", []):
                        if attr.get("id") == "GTIN":
                            gtin = attr.get("value_name")
                            break
                    product_code = gtin or sku
   
                    query = {
                        'q_columns': ['a.id','a.meli_id'],
                        'q_from':f'FROM {SCHEMA_INVENTORY}.{PRODUCTS_TABLE} as a',
                        'q_where': f"WHERE a.meli_id = '{meli_id}'",
                        'q_limit':'LIMIT 1'
                    }
                    logger.info("Searching product by meli id")
                    data = get_method(query)
                    if data is None:
                        logger.info("Failed to search by Meli id")
                        logger.info("Searching product by product code (sku/gtin)")
                        query['q_where'] = f"WHERE a.product_code = '{product_code}'"
                        data = get_method(query)
                        if data is None:
                            logger.info("Failed to search by product code")
                            logger.info("Searching product by listing catalog")
                            id_format = json.dumps([{"id": meli_id}])
                            query = {
                                'q_columns': ['a.meli_id','a.listing_catalog','b.id'],
                                'q_from':f'FROM {SCHEMA_MERCADOLIBRE}.{PROD_STATUS_TABLE_MELI} as a',
                                'q_join':[f'LEFT JOIN {SCHEMA_INVENTORY}.{PRODUCTS_TABLE} as b on b.meli_id = a.meli_id'],
                                'q_where': f"WHERE json_contains(a.listing_catalog, '{id_format}')",
                            }
                            data = get_method(query)
                            if data is None or len(data) > 1:
                                logger.info("Failed to search by listting catalog")
                                logger.info("The result was either None or returned more than one result.")
                                message = f"""It was not possible to track succesfully the product sold inside our DB.\n 
                                OrderID: {order_id}"""
                                enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, message)
                                return

                    data = data[0]
                    logger.info(data)
                    quantity = item_info.get('quantity') * DEVOLUTION_MULTIPLIER
                    unit_price = item_info.get('unit_price')
                    id = data.get('id')
                    sell_workflow(order_id, id, quantity, unit_price)

            else:
                logger.error(f"Error processing the order: {response.json()}")
                message = f"fallo en la orden de mercadolibre: {order_id}\n {response.json()}"
                enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, message)
                return


        elif platform == 'tienda_nube':

            if get_order(order_id, platform):
                logger.info(f"Order: {order_id} already processed, skipping.")
                return

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
                logger.info("Order Dict Created. saving order in DB.")
                insert_order(order, platform)
                data = get_tienda_nube_id(product_id)
                id = data.get('id')
                sell_workflow(order_id, id, quantity, price)

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


