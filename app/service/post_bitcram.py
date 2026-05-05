import requests
import json
from app.utils.logger import logger
from app.settings.config import BASE_URL, CHECKOUT_NUMBER, PHONE_INTERNAL, TOKEN_WHAPI
from app.service.notifications import enviar_mensaje_whapi
from app.service.secrets import bitcram_secrets


def sell_workflow(target_product_id, quantity, price):

    headers = {"Authorization": f"Bearer {bitcram_secrets()}"}

    commercial_doc, warehouse_id = create_commercial_doc(target_product_id, quantity, price, headers)
    previous_stock = get_current_stock(target_product_id, warehouse_id, headers)
    response = post_sell(commercial_doc, headers)
    if response is True:
        current_stock = get_current_stock(target_product_id, warehouse_id, headers)
        notify_sell(target_product_id, previous_stock, current_stock)

def get_current_stock(p_id, w_id, headers):
    response = requests.get(
        f"{BASE_URL}/api/stock_items/index",
        headers=headers,
        params={
            "list_light": "true", 
            "where": json.dumps({
                "warehouse_id": w_id,
                "product_id": p_id
            })
        }
    )
    if response.raise_for_status() is None:
        items_stock = response.json().get("items", [])
        stock = items_stock[0].get("product_balance", 0)
        logger.info(f"Current Stock: {stock}")
        return stock
    else:
        logger.error(f"Failed to Retrieve stock product befor update, reason:{response.raise_for_status()} ")


def get_payment_id(checkout_session_id, headers):

    response= requests.get(
        f"{BASE_URL}/api/checkout_sessions/index/{checkout_session_id}",
        headers=headers,
    )
    if response.raise_for_status() is None:
        response = response.json()
        checkout_session_accounts = response.get("checkout_session_accounts", [])   
        if not checkout_session_accounts:
            logger.info(f"No se encontraron cuentas para la sesión de caja numer: {checkout_session_id}")
        payment_type_id = checkout_session_accounts[0].get("checkout_account", {}).get("payment_type", {}).get("id")
        logger.info(f"Payment Type ID: {payment_type_id}") 
        return payment_type_id
    else:
        logger.error(f"Failed to get payment_type_id{response.json()}")


def create_commercial_doc(target_product_id, quantity, price, headers):
    response = requests.get(
        f"{BASE_URL}/api/checkouts/index",
        headers=headers,
        params={
            "where": json.dumps({
                "checkouts.checkout_number": CHECKOUT_NUMBER
            })
        }
    )
    if response.raise_for_status() is None: 
        response = response.json()  
        checkout_items = response.get("items", [])
        checkout = checkout_items[0]
        warehouse_id = checkout.get("warehouse", {}).get("id")
        checkout_session_id = checkout.get("last_checkout_session", {}).get("id")
        is_open = checkout.get("is_open")
        logger.info(f"Warehouse ID: {warehouse_id}")
        logger.info(f"Checkout Session ID: {checkout_session_id}")
        logger.info(f"Is Open: {is_open}")

        if not is_open:
            logger.info(f"La caja número {CHECKOUT_NUMBER} está cerrada !!!")
            return "ERROR"

        
        payment_type_id = get_payment_id(checkout_session_id, headers)
        

        # COMMERCIAL_DOC -> guarda venta !!!
        items = [
            {
            "quantity": quantity,
            "unit_price": price,
            "stock_mov_item": {
                    "stock_item": {
                        "product": {"id": target_product_id,},
                        "warehouse": {"id": warehouse_id}
                    }
                }
            }
        ]   

        payment = [
            {
            "amount": quantity * price,
            "payment_type_id": payment_type_id,
            "payment_type": {"id": 298}
            }
        ]   

        commercial_doc = {
            "checkout_session": {"id": checkout_session_id},
            "iva_condition": {"id": "CF"},
            "items": items,
            "payments": payment}    
        logger.info("Commercial doc created.")
        return commercial_doc, warehouse_id
    
    else:
        return "ERROR"
    

def post_sell (commercial_doc, headers):

    response = requests.post(
        f"{BASE_URL}/api/commercial_docs/index",
        headers=headers,
        json=commercial_doc
    )

    if response.status_code > 300:
        error = response.json()
        logger.error(f"Error posting sell: {error}")
        message = f"Error Publicando venta en Bitcram: '\n' {error}"
        enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, message)
        return False

    else:
        response = response.json()
        commercial_doc_id = response.get("id")
        commercial_doc_number = response.get("commercial_doc_number")
        #PUBLICAR EN DB Y RELACIONAR CON ORDER ID
        return True


def notify_sell(target_product_id, previous_stock, current_stock):

    message_before = f"[STOCK] del item: '{target_product_id}' antes de la venta: {previous_stock}"
    message_after = f"[STOCK] del item:'{target_product_id}' después de la venta: {current_stock}"
    logger.info(message_before)  
    logger.info(message_after)
    message_complete = 'meli_order_id: ' + str(target_product_id) + '\n' + message_before + '\n' + message_after
    enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, message_complete)
    return None