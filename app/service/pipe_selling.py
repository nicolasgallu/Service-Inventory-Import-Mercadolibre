from app.utils.logger import logger
from app.service.secrets import meli_secrets
from app.service.database import get_order, insert_order, get_bitcram_data
import requests

def pipeline_selling(order_id):
    """"""
    if get_order(order_id):
        logger.info(f"Order: {order_id} already processed, skipping.")
        return
    
    logger.info(f"New sale notification received: {order_id}")

    try:
        logger.info("Running sell procesing..")
        
        token = meli_secrets()
        url = f"https://api.mercadolibre.com/orders/{order_id}"
        headers = {'Authorization': f'Bearer {token}'}
        
        #Request order details from MeLi API
        response = requests.get(url, headers=headers)
        order_data = response.json()
        
        #Extract unique Order ID and sale date
        order_id = order_data.get('id')
        created_at = order_data.get('date_created')
        order_items = order_data.get('order_items', [])

        order = {'id':order_id,'data': order_items ,'created_at': created_at}
        insert_order(order)
        
        #(using loop cause there can be multiple differents items in one single purcharse)
        for item_info in order_items:
            meli_id = item_info.get('item', {}).get('id')
            quantity = item_info.get('quantity')
            data = get_bitcram_data(meli_id)
            id = data.get('id')
            cost = float(data.get('cost'))
            ##!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            ##CONTINUAR ACA CONSULTANDO EL ID DE BITCRAM Y POSTEANDO VENTA EN DB.
            ##!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

            ##EL CODIGO DEBE SER ASYNC PARA PROCESAR VARIAS SOLICITUDES EN SIMULTANEO.


    except Exception as e:
        logger.error(f"Error processing the order: {e}")


