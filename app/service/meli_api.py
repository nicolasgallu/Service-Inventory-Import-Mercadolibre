import requests
import ast
from app.utils.logger import logger
from app.service.notifications import enviar_mensaje_whapi
from app.service.ai_completation import completing_fields
from app.service.database import load_meli_id
from app.settings.config import (
    TOKEN_WHAPI, PHONES, CURRENCY, BUY_MODE, CONDITION, 
    LISTING_TYPE, MODE, LOCAL_PICK_UP, FREE_SHIPPING, WARRANTY_TYPE,WARRANTY_TIME, DS_API_KEY, PROMPT_SYS_MELI)




###/////////////////////FUNCIONES AUXILIARES///////////////////////////###
def get_category_id(product_name, token):
    """Generate category ID trough Mercadolibre AI"""
    logger.info("Getting category ID from Meli API..")
    response = requests.get("https://api.mercadolibre.com/sites/MLA/domain_discovery/search", 
                            params={"q": product_name, "limit": 1}, 
                            headers={"Authorization": f"Bearer {token}"})
    if response.status_code == 200 and response.json():
        category_id = response.json()[0].get("category_id", None)
        logger.info(f"Category ID Selected: {category_id}")
        return category_id
    return None


def set_description(meli_id, description, token):

    logger.info(f"Writting Description in product: {meli_id}")
    url = f"https://api.mercadolibre.com/items/{meli_id}/description"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"}
    
    payload = {"plain_text": description}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code in [200, 201]:
        logger.info(f"Description loaded for product: {meli_id}")
    else:
        logger.error(f"Failed to load description for product {meli_id}: {response.status_code} - {response.text}")
    return response.json()



def update_description(meli_id, description, token):

    url = f"https://api.mercadolibre.com/items/{meli_id}/description"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"}
    payload = {"plain_text": description}
    response = requests.put(url, json=payload, headers=headers)
    if response.status_code in [200, 204]:
        logger.info(f"Description of product: {meli_id} succesfully updated")
    else:
        logger.error(f"Description of product {meli_id} failed to updated: {response.status_code} - {response.text}")
    return response



def get_required_attributes(category_id, token):
    """
    Consulta los atributos obligatorios ignorando los campos constantes 
    (GTIN, IVA, Impuestos, etc.)
    """
    if not category_id:
        return []

    EXCLUDED_IDS = {
        "VALUE_ADDED_TAX", 
        "IMPORT_DUTY",
        "EMPTY_GTIN_REASON"
    }

    url = f"https://api.mercadolibre.com/categories/{category_id}/attributes"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        all_attributes = response.json()
        
        required_attrs = [
            {
                "id": attr["id"],
                "name": attr["name"],
                "value_type": attr.get("value_type"),
                "allowed_values": attr.get("values", [])
            }
            for attr in all_attributes 
            if (
                ("required" in attr.get("tags", []) or "conditional_required" in attr.get("tags", [])) 
                and attr["id"] not in EXCLUDED_IDS 
            )
        ]
        
        logger.info(f"Required Attributes (filtered): {[a['id'] for a in required_attrs]}")
        return required_attrs

    except Exception as e:
        logger.error(f"Error fetching attributes for {category_id}: {e}")
        return []



def item_reactivate(meli_id, token):
    """
    Busca el ítem. Si está pausado, intenta republicarlo.
    """
    logger.info(f"Validating current status for item: {meli_id}")
    
    # 1. Consultar el estado actual del ítem
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"https://api.mercadolibre.com/items/{meli_id}", 
        headers=headers
    )
    status = response.json().get('status')

    # 2. Condición: Si está pausado, republicar ############################### solo pausados? y si estan en un estado como inactivo?
    if status == 'paused':
        logger.info(f"Item {meli_id} is PAUSED. Attempting to re-activate...")

        url = f"https://api.mercadolibre.com/items/{meli_id}"
        payload = {"status": "active"}
        response = requests.put(url, json=payload, headers=headers)

        if response.status_code == 200:
            logger.info(f"Item {meli_id} is now ACTIVE.")
            return True
        else:
            logger.error(f"Failed to re-activate item {meli_id}: {response.text}")
            message = f"""Fallo en la etapa de reactivar el item: {meli_id} en Mercadolibre.
                        la respuesta fue\n {response.text}"""
            enviar_mensaje_whapi(TOKEN_WHAPI, PHONES, message)
            return False
    return True





###/////////////////////PUBLISH EVENT///////////////////////////###
def publish_item(item_data, public_images, token):
    """publish the item with a second try option"""

    brand, description = completing_fields(item_data)

    ####TRYING TO PUBLISH FIRST TIME####
    logger.info(f"Attempting to create Item: {item_data['id']} in mercadolibre..")
    
    category_id = get_category_id(item_data["product_name"], token)
    required_attrs = get_required_attributes(category_id, token)

    item_format = {
        "title": item_data["product_name"], 
        "category_id": category_id, 
        "price": item_data["price"], 
        "currency_id": CURRENCY, 
        "available_quantity": item_data["stock"],
        "buying_mode": BUY_MODE, 
        "condition": CONDITION, 
        "listing_type_id": LISTING_TYPE,
        "pictures": [public_images], 
        "attributes": [
            {"id": "EAN", "value_name": item_data["product_code"]}, 
            {"id": "BRAND", "value_name": brand},
            {"id": "MODEL", "value_name": None},
            {"id": "VALUE_ADDED_TAX", "value_id": "48405909"},#48405909 es el 21% 55043032 excento y 48405907 es 0%
            {"id": "IMPORT_DUTY", "value_id": "49553239"}, #49553239 es 0
            {"id": "EMPTY_GTIN_REASON", "value_id": "17055160"},#Bitcram no tiene GTIN
            {"id": "UNITS_PER_PACK", "value_name": "1"}
            
        ],
        "shipping": {
            "mode": MODE, 
            "local_pick_up": LOCAL_PICK_UP,
            "free_shipping": FREE_SHIPPING 
        },
        "sale_terms": [
            {"id": "WARRANTY_TYPE", "value_name": WARRANTY_TYPE}, 
            {"id": "WARRANTY_TIME", "value_name": WARRANTY_TIME},
        ]
    }

    try:
        response = requests.post("https://api.mercadolibre.com/items", 
                    json=item_format,
                    headers={"Authorization": f"Bearer {token}"})
        
    except Exception as error:
        return error
    
    if response.status_code in [200, 201]:
        meli_id = response.json().get('id')
        logger.info(f"Publish of the item: {meli_id} successfully made.")
        set_description(meli_id, description, token)
        load_meli_id(item_data['id'], {'meli_id': meli_id})
        return
    


    ####TRYING TO PUBLISH SECOND TIME####
    else:
        logger.warning(f"Failed to create item, response: {response.status_code}")
        logger.info("using AI to publish item (using restricted scopes).")
    
        prompt_usr = f"""
        ERROR_API: {response.status_code} - {response.json()}
        PAYLOAD_ORIGINAL: {item_format}
        REQUIRED_ATTRIBUTES: {required_attrs}"""
        
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
            "max_tokens": 2000,
            "temperature": 0.45
        }       

        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
        item_data_fix = response.json()['choices'][0]['message']['content']
        logger.info(f"Data Generada por AI para publicar en Meli: {item_data_fix}")
        
        #Trying to publish the item now with AI correction.
        item_data_fix=  ast.literal_eval(item_data_fix)
        response = requests.post("https://api.mercadolibre.com/items", 
                                 json=item_data_fix, 
                                 headers={"Authorization": f"Bearer {token}"})

        if response.status_code in [200, 201]:
            meli_id = response.json().get('id')
            logger.info(f"Publish of the item: {meli_id} successfully made in the second try.")
            set_description(meli_id, description, token)
            load_meli_id(item_data['id'], {'meli_id': meli_id})
            return
        
        else:
            logger.error(f"Failed to create item, response: {response.status_code} \n {response.json()}")
            message = f"""Fallo la publicacion del item {item_data['id']} en Mercadolibre.La respuesta fue:\n 
            {response.json()}"""
            enviar_mensaje_whapi(TOKEN_WHAPI,PHONES,message)
            return






###/////////////////////UPDATE EVENT///////////////////////////###
def update_item(item_data, public_images, token):

    meli_id = item_data['meli_id']
    price = item_data['price'] 
    stock = item_data['stock'] 
    description = item_data['description'] 

    logger.info(f"Attempting to update Item: {meli_id} from mercadolibre..")


    ####FIRST WE UPDATE ALL VALUES ALLOWED (except description)####
    new_data = { "price": price, "available_quantity": stock, "pictures": public_images}

    response = requests.put(f"https://api.mercadolibre.com/items/{meli_id}", 
                            json=new_data, 
                            headers={"Authorization": f"Bearer {token}"})

    if response.status_code in [200, 201]:
        ####UPDATING DESCRIPTION####
        update_description(meli_id, description, token)
        if item_reactivate(meli_id, token):
            logger.info(f"Update of the item: {meli_id} successfully made.")
            return
    
    else:
        logger.error(f"Failed to update item: {meli_id} \n {response.json()}")
        message = f"""Fallo la actualizacion del item {item_data["id"]} en Mercadolibre.La respuesta fue:\n
        {response.json()}"""
        enviar_mensaje_whapi(TOKEN_WHAPI, PHONES, message)
        return
        


###/////////////////////PAUSED EVENT///////////////////////////###
def pause_item(item_data, token):
    """Changes item status to paused in Mercado Libre"""
    meli_id = item_data['meli_id'] 

    logger.info(f"Attempting to pause item: {meli_id}")
    
    try:
        response = requests.put(
            f"https://api.mercadolibre.com/items/{meli_id}", 
            json={"status": "paused"},
            headers={ "Authorization": f"Bearer {token}", "Content-Type": "application/json"})
        
        if response.status_code == 200:
            logger.info(f"Item {meli_id} successfully paused (status: paused).")
            return
        else:
            logger.error(f"Failed to pause item {meli_id}. Status: {response.status_code}, Error:\n {response.json()}")
            enviar_mensaje_whapi(TOKEN_WHAPI, PHONES, response.json())
            return

    except Exception as error:
        logger.error(f"Unexpected error while pausing {meli_id}:\n {str(error)}")
        enviar_mensaje_whapi(TOKEN_WHAPI, PHONES, error)
        return
