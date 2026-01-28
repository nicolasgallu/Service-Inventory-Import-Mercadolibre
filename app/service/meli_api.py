import requests
import ast
from app.utils.logger import logger
from app.settings.config import (
    TOKEN_WHAPI, PHONES, CURRENCY, BUY_MODE, CONDITION, 
    LISTING_TYPE, MODE, LOCAL_PICK_UP, FREE_SHIPPING, WARRANTY_TYPE,WARRANTY_TIME, DS_API_KEY, PROMPT_SYS_MELI)
from app.service.notifications import enviar_mensaje_whapi


def get_category_id(product_name, token):
    """Generate category ID trough Mercadolibre AI"""
    logger.info("Getting category ID from Meli API")
    response = requests.get("https://api.mercadolibre.com/sites/MLA/domain_discovery/search", 
                            params={"q": product_name, "limit": 1}, 
                            headers={"Authorization": f"Bearer {token}"})
    if response.status_code == 200 and response.json():
        category_id = response.json()[0].get("category_id", None)
        return category_id
    return None


def item_status(meli_id, token):
    """
    Busca el ítem. Si está cerrado, intenta republicarlo.
    """
    logger.info(f"Checking status for item: {meli_id}")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Consultar el estado actual del ítem
    response = requests.get(
        f"https://api.mercadolibre.com/items/{meli_id}", 
        headers=headers
    )

    status = response.json().get('status')

    # 2. Condición: Si está cerrado, republicar
    if status == 'paused':
        logger.info(f"Item {meli_id} is PAUSED. Attempting to re-activate...")

        url = f"https://api.mercadolibre.com/items/{meli_id}"
        payload = {"status": "active"}
        response = requests.put(url, json=payload, headers=headers)

        if response.status_code == 200:
            logger.info(f"Item {meli_id} is now ACTIVE.")
            return True
        
        else:
            logger.error(f"Failed to activate item {meli_id}: {response.text}")
            message = f"""Fallo en la etapa de reactivar el item: {meli_id} en Mercadolibre.
                        la respuesta fue {response.text}"""
            enviar_mensaje_whapi(TOKEN_WHAPI, PHONES, message)
            return False
        
    return True



def publish(item_data, meli_id, token):
    """publish take the task both for updating an existing product or creating a new one."""

    product_name = item_data['product_name']

    ####CHECKING IF ITEM EXISTS IN MELI####
    if meli_id:
        logger.info("Item already exist, updating data..")
        
        if item_status(meli_id, token):

            data_update = {
                "price": item_data["price"],
                "available_quantity": item_data["stock"],
                "pictures": [{"source": item_data["product_image_b_format_url"]}]
            }
            response = requests.put(f"https://api.mercadolibre.com/items/{meli_id}", 
                                    json=data_update, 
                                    headers={"Authorization": f"Bearer {token}"})

            if response.status_code in [200, 201]:
                logger.info(f"Update of the item: {meli_id} successfully made.")
                return None

            else:
                logger.error(f"Failed to update item: {meli_id} / {response.json()}")
                message = f"""Fallo la actualizacion del item {product_name} en Mercadolibre.
                            la respuesta fue {response.json()}"""
                enviar_mensaje_whapi(TOKEN_WHAPI, PHONES, message)
                return None
        else:
            return None


    ####TRYING TO PUBLISH FIRST TIME####
    logger.info("Item doesnt exist, creating..")
    category = get_category_id(product_name, token)
    item_format = {
        "title": item_data["product_name"], 
        "category_id": category, 
        "price": item_data["price"], 
        "currency_id": CURRENCY, 
        "available_quantity": item_data["stock"],
        "buying_mode": BUY_MODE, 
        "condition": CONDITION, 
        "listing_type_id": LISTING_TYPE,
        "pictures": [{"source": item_data["product_image_b_format_url"]}],
        "description": {"plain_text": item_data['description']}, 
        "attributes": [
            {"id": "EAN", "value_name": item_data["product_code"]}, 
            {"id": "BRAND", "value_name": item_data['brand']},
            {"id": "MODEL", "value_name": None},
        ],
        "shipping": {
            "mode": MODE, 
            "local_pick_up": LOCAL_PICK_UP,
            "free_shipping": FREE_SHIPPING 
        },
        "sale_terms": [
            {"id": "WARRANTY_TYPE", "value_name": WARRANTY_TYPE}, 
            {"id": "WARRANTY_TIME", "value_name": WARRANTY_TIME} 
        ]
    }
    
    response = requests.post("https://api.mercadolibre.com/items", 
                             json=item_format, 
                             headers={"Authorization": f"Bearer {token}"})

    if response.status_code in [200, 201]:
        meli_id = response.json().get('id')
        logger.info(f"Publish of the item: {meli_id} successfully made.")
        return {"meli_id": meli_id}
    

    ####TRYING TO PUBLISH SECOND TIME####
    else:
        logger.warning(f"Failed to create item {response.status_code}")
        logger.info("using AI in order to trying to publish the item (with restricted scope).")
    
        prompt_usr = f"""
                la respuesta que recibi a la hora de publicar el producto fue: {response.status_code}: {response.json()}.
                Este es dict con todos los datos que estoy usando para realizar la publicacion: {item_format}
                """
        headers = {
            "Authorization": f"Bearer {DS_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "deepseek-chat",
            "messages": [
                    {"role": "system", "content": PROMPT_SYS_MELI},
                    {"role": "user", "content": prompt_usr}
                ],
            "max_tokens": 1500,
            "temperature": 0.45
        }       
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
        item_data_fix = response.json()['choices'][0]['message']['content']
        item_data_fix=  ast.literal_eval(item_data_fix)

        #Trying to publish the item now with AI correction.
        response = requests.post("https://api.mercadolibre.com/items", 
                                 json=item_data_fix, 
                                 headers={"Authorization": f"Bearer {token}"})

        if response.status_code in [200, 201]:
            meli_id = response.json().get('id')
            logger.info(f"Publish of the item: {meli_id} successfully made.")
            return {"meli_id": meli_id}
        
        else:
            logger.error(f"Failed to create item {response.status_code} / {response.json()}")
            message = f"""Fallo la actualizacion del item {product_name} en Mercadolibre.
                    la respuesta fue {response.json()}"""
            enviar_mensaje_whapi(TOKEN_WHAPI,PHONES,message)
            return None



def pause_item(item_id, token):
    """Changes item status to paused in Mercado Libre"""
    logger.info(f"Attempting to pause item: {item_id}")
    
    try:
        response = requests.put(
            f"https://api.mercadolibre.com/items/{item_id}", 
            json={"status": "paused"},
            headers={ "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        
        if response.status_code == 200:
            logger.info(f"Item {item_id} successfully paused (status: paused).")
            return True
        else:
            logger.error(f"Failed to pause item {item_id}. Status: {response.status_code}, Error: {response.json()}")
            enviar_mensaje_whapi(TOKEN_WHAPI, PHONES, response.json())
            return False

    except Exception as error:
        logger.error(f"Unexpected error while pausing {item_id}: {str(error)}")
        enviar_mensaje_whapi(TOKEN_WHAPI, PHONES, error)
        return False