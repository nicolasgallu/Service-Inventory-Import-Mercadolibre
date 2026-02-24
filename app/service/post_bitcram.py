import requests
import json
from app.utils.logger import logger
from app.settings.config import BASE_URL, CHECKOUT_NUMBER, PHONES, USERNAME, PASSWORD
from app.service.notifications import enviar_mensaje_whapi
from app.service.secrets import bitcram_secrets


#TEMPORAL... solo para testear ventas
resp = requests.post(
    f"{BASE_URL}/api/auth/",
    json={"username": USERNAME, "password": PASSWORD}
)
resp.raise_for_status()
resp = resp.json()
token = resp.get("token")




def post_sell(target_product_id, quantity, price):
    #//////////////////////CHECKOUT//////////////////////

    #token = bitcram_secrets() -----DESCOMENTAR
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(
        f"{BASE_URL}/api/checkouts/index",
        headers=headers,
        params={
            "where": json.dumps({
                "checkouts.checkout_number": CHECKOUT_NUMBER # Ajustado según tu segundo snippet
            })
        }
    )
    resp.raise_for_status()
    resp = resp.json()  

    checkout_items = resp.get("items", [])
    if not checkout_items:
        raise Exception(f"No se encontró la caja número {CHECKOUT_NUMBER}") 

    checkout = checkout_items[0]
    warehouse_id = checkout.get("warehouse", {}).get("id")
    price_list_id = checkout.get("price_list", {}).get("id")
    checkout_session_id = checkout.get("last_checkout_session", {}).get("id")
    is_open = checkout.get("is_open")
    logger.info("Warehouse ID: ", warehouse_id)
    logger.info("Price List ID: ", price_list_id)
    logger.info("Checkout Session ID: ", checkout_session_id)
    logger.info("Is Open: ", is_open)
    if not is_open:
        logger.info(f"La caja número {CHECKOUT_NUMBER} está cerrada !!!")
        exit()  

    #//////////////////////CHECKOUT SESSION//////////////////////
    resp = requests.get(
        f"{BASE_URL}/api/checkout_sessions/index/{checkout_session_id}",
        headers=headers,
    )
    resp.raise_for_status()
    resp = resp.json()
    checkout_session_accounts = resp.get("checkout_session_accounts", [])   

    if not checkout_session_accounts:
        raise Exception(f"No se encontraron cuentas para la sesión de caja número {checkout_session_id}")
    payment_type_id = checkout_session_accounts[0].get("checkout_account", {}).get("payment_type", {}).get("id")
    logger.info("Payment Type ID: ", payment_type_id) 

    #//////////////////////LÓGICA DE STOCK BASADA EN TU FUNCIÓN GET_STOCK//////////////////////
    def consultar_stock_especifico(p_id, w_id, token_auth):
        """Adaptación de tu función get_stock para un solo producto"""
        response = requests.get(
            f"{BASE_URL}/api/stock_items/index",
            headers={"Authorization": f"Bearer {token_auth}"},
            params={
                "list_light": "true", 
                "where": json.dumps({
                    "warehouse_id": w_id,
                    "product_id": p_id # Filtramos por el producto que nos interesa
                })
            }
        )
        response.raise_for_status()
        items_stock = response.json().get("items", [])
        logger.info(f"print del item stock: {items_stock}")
        if items_stock:
            # Según tu código, el stock está en 'product_balance'
            return items_stock[0].get("product_balance", 0)
        return 0    


    #//////////////////////PREPARING POST EVENT//////////////////////
    stock_antes = consultar_stock_especifico(target_product_id, warehouse_id, token)
    # DATA POST CAMBIO DE STOCK
    # (Mantenemos la estructura original del post de venta)
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
        "amount": quantity*price,
        "payment_type_id": payment_type_id,
        "payment_type": {"id": 298}
        }
    ]   

    commercial_doc = {
        "checkout_session": {"id": checkout_session_id},
        "iva_condition": {"id": "CF"},
        "items": items,
        "payments": payment}    

    #//////////////////////EXECUTING POST EVENT//////////////////////
    resp = requests.post(f"{BASE_URL}/api/commercial_docs/index", headers=headers, json=commercial_doc)
    ## --- COMPROBACIÓN FINAL ---
    resp.raise_for_status()
    resp = resp.json()
    commercial_doc_id = resp.get("id")
    commercial_doc_number = resp.get("commercial_doc_number")
    logger.info("Commercial Doc Number: ", commercial_doc_number)
    logger.info("Commercial Doc ID: ", commercial_doc_id)
    stock_despues = consultar_stock_especifico(target_product_id, warehouse_id, token)
    message_before = f"[STOCK] '{target_product_id}' antes de la venta: {stock_antes}"
    message_after = f"[STOCK] '{target_product_id}' después de la venta: {stock_despues}"
    logger.info(message_before)  
    logger.info(message_after)
    message_complete = message_before + '\n' + message_after
    enviar_mensaje_whapi(token, PHONES, message_complete)
