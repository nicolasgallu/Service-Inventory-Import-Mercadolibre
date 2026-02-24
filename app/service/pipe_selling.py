from app.utils.logger import logger
from app.service.secrets import meli_secrets
from app.service.database import get_order, insert_order, get_bitcram_data
from app.service.post_bitcram import post_sell
from app.service.notifications import enviar_mensaje_whapi
from app.settings.config import PHONES
import requests
import json

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
        #############################response = requests.get(url, headers=headers)
        #############################order_data = response.json()

        order_data = {
            "id": 2000003508419013,
            "date_created": "2024-02-24T10:01:50.000-04:00",
            "last_updated": "2024-02-24T10:10:20.000-04:00",
            "expiration_date": "2024-03-24T10:01:50.000-04:00",
            "total_amount": 1500.00,
            "currency_id": "ARS",
            "order_items": [
                {
                    "item": {
                        "id": "MLA2900326752",
                        "title": "Producto de Prueba - No ofertar",
                        "category_id": "MLA1234",
                        "variation_id": 456789123,
                        "seller_custom_field": None
                    },
                    "quantity": 1,
                    "unit_price": 1500.00,
                    "full_unit_price": 1500.00,
                    "currency_id": "ARS"
                }
            ],
            "buyer": {
                "id": 987654321,
                "nickname": "TEST_USER_123",
                "first_name": "Test",
                "last_name": "User",
                "email": "test_user_123@testuser.com",
                "phone": {
                    "area_code": "11",
                    "number": "12345678"
                },
                "billing_info": {
                    "doc_type": "DNI",
                    "doc_number": "12345678"
                }
            },
            "seller": {
                "id": 12345678
            },
            "payments": [
                {
                    "id": 55152514332,
                    "status": "approved",
                    "transaction_amount": 1500.00,
                    "payment_method_id": "account_money",
                    "date_approved": "2024-02-24T10:01:55.000-04:00"
                }
            ],
            "shipping": {
                "id": 41234567890
            },
            "status": "paid"
        }
        
        #Extract unique Order ID and sale date
        order_id = order_data.get('id')
        created_at = order_data.get('date_created')
        order_items = order_data.get('order_items', [])

        order = {'id':order_id,'data': json.dumps(order_items) ,'created_at': created_at}
        insert_order(order)
        
        #(using loop cause there can be multiple differents items in one single purcharse)
        logger.info(f"data de la orden cruda: {order_data}")
        message= f'nueva orden generada\n {order_data}' 
        enviar_mensaje_whapi(token, PHONES, message)
        for item_info in order_items:
            meli_id = item_info.get('item', {}).get('id')
            quantity = item_info.get('quantity')
            unit_price = item_info.get('unit_price')
            data = get_bitcram_data(meli_id)
            id = data.get('id')

            post_sell(id, quantity, unit_price)

    except Exception as e:
        logger.error(f"Error processing the order: {e}")


