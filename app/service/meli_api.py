import ast
import requests
from app.utils.logger import logger
from app.service.notifications import enviar_mensaje_whapi
from app.service.database import load_meli_data, load_failed_status
from app.service.bot import call_ai
from app.settings.config import (
    TOKEN_WHAPI, PHONES, CURRENCY, BUY_MODE, CONDITION, 
    LISTING_TYPE, MODE, LOCAL_PICK_UP, FREE_SHIPPING, WARRANTY_TYPE, WARRANTY_TIME, PROMPT_SYS_MELI, PROMPT_FAILED)


def publish_item(item_data, public_images, token):
    """publish the item with a second try option"""

    logger.info("checking if product is already publish..")
    if item_data['meli_id']:
        logger.warning(f"""Item: {item_data['id']} already exists in mercadolibre 
            under this ID: {item_data['meli_id']} nothing to do.""")
        return
    
    logger.info("checking if product accoumplish minimum price value..")    
    if item_data["price"] < 1000 or item_data["price"] is None:
        logger.error("Product Price < $1000")
        item_metadata = {'status': 'no publicado','reason': 'precio del producto no cumple el minimo de MercadoLibre'}
        load_failed_status(item_data['id'], item_metadata)
        return

    logger.info("Getting Category ID..")    
    category_id = get_category_id(item_data["product_name"], token)
    if category_id is None:
        item_metadata = {
            'status': 'no publicado',
            'reason': 'Mercadolibre no logro crear un category ID, se recomienda modificar el titulo u intentar publicar manualmente.'}
        load_failed_status(item_data['id'], item_metadata)
        return
    
    logger.info("Attempting to publish the product in mercadolibre..")
    item_format = {
        "title": item_data["product_name_meli"], 
        "category_id": category_id, 
        "price": float(item_data["price"]), 
        "currency_id": CURRENCY, 
        "available_quantity": item_data["stock"],
        "buying_mode": BUY_MODE, 
        "condition": CONDITION, 
        "listing_type_id": LISTING_TYPE,
        "pictures": public_images, 
        "attributes": [
            {"id": "BRAND", "value_name": item_data["brand"]},
            {"id": "MODEL", "value_name": None},
            {"id": "VALUE_ADDED_TAX", "value_id": "48405909"},#48405909 es el 21% 55043032 excento y 48405907 es 0%
            {"id": "IMPORT_DUTY", "value_id": "49553239"}, #49553239 es 0
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

    if len(item_data['product_code']) not in [8,12,13,14]:
        product_code = {"id": "SELLER_SKU", "value_name": item_data['product_code']}
        attr_gtin = {"id": "GTIN", "value_name": "N/A"}
        gtin_reason = {"id": "EMPTY_GTIN_REASON", "value_id": "17055160"}
        item_format['attributes'].append(product_code)
        item_format['attributes'].append(attr_gtin)
        item_format['attributes'].append(gtin_reason)
    else:
        product_code = {"id": "GTIN", "value_name": item_data['product_code']}
        item_format['attributes'].append(product_code)

    try:
        response = requests.post("https://api.mercadolibre.com/items", 
                    json=item_format,
                    headers={"Authorization": f"Bearer {token}"})
        
    except Exception as error:
        logger.error(error)
        p_second_attempt(item_data, item_format, category_id, token)
    
    if response.status_code in [200, 201]:
        logger.info("Publish of the item successfully made.")
        meli_id = response.json().get('id')
        permalink = response.json().get('permalink')
        item_metadata = {'meli_id': meli_id, 'permalink': permalink}
        set_description(meli_id, item_data["description"], token)
        load_meli_data(item_data['id'], item_metadata)
        return

def update_item(item_data, public_images, token):
    """Update MercadoLibre item"""
    meli_id = item_data['meli_id']
    if meli_id is None:
        logger.error(f"Item: {item_data['item_id']} doesnt exists in mercadolibre, nothing to update.")
        return
    if item_data['price'] < 1000 or item_data['price'] is None:
        logger.error("Product Price < $1000")
        item_metadata = {'status': 'no actualizado','reason': 'precio del producto no cumple el minimo de MercadoLibre'}
        load_failed_status(item_data['id'], item_metadata)
        return
    
    logger.info(f"Attempting to update Item: {meli_id} from mercadolibre..")
    new_data = { "price": float(item_data['price']) , 
         "available_quantity": item_data['stock'] , 
         "pictures": public_images
         
    }
    response = requests.put(f"https://api.mercadolibre.com/items/{meli_id}", 
                            json=new_data, 
                            headers={"Authorization": f"Bearer {token}"})
    
    if response.status_code in [200, 201]:
        set_description(meli_id, item_data['description'] , token)
        item_reactivate(meli_id, token)
        return
    else:
        logger.error(f"Failed to update item: {meli_id} \n {response.json()}")
        message = f"""Fallo la actualizacion del item {meli_id} en Mercadolibre. La respuesta fue:\n
        {response.json()}"""
        enviar_mensaje_whapi(TOKEN_WHAPI, PHONES, message)
        return
        
def pause_item(item_data, token):
    """Changes item status to paused in Mercado Libre"""
    meli_id = item_data['meli_id'] 
    if meli_id is None:
        logger.error(f"Item: {item_data['id']} doesnt exists in mercadolibre, nothing to pause.")
        return

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



def p_second_attempt(item_data, item_format, category_id, token):
    """AI modifies attributes in order to publish the product in meli"""

    logger.info("using AI to publish item (using restricted scopes).")
    required_attrs = get_required_attributes(category_id, token)
    usr_prompt = f"""
        ERROR_API: {response.status_code} - {response.json()}
        PAYLOAD_ORIGINAL: {item_format}
        REQUIRED_ATTRIBUTES: {required_attrs}"""

    item_data_fix = call_ai(usr_prompt, PROMPT_SYS_MELI)
    item_data_fix=  ast.literal_eval(item_data_fix)
    response = requests.post("https://api.mercadolibre.com/items", 
                             json=item_data_fix, 
                             headers={"Authorization": f"Bearer {token}"})
    if response.status_code in [200, 201]:
        logger.info("Publish of the item successfully made in the second try.")
        meli_id = response.json().get('id')
        permalink = response.json().get('permalink')
        item_metadata = {'meli_id': meli_id, 'permalink': permalink}
        set_description(meli_id, item_data["description"], token)
        load_meli_data(item_data['id'], item_metadata)
        return
    else:
        logger.error(f"Failed to create item, response: {response.status_code} \n {response.json()}")
        usr_prompt = f"""ERROR AL INTENTAR PUBLICAR EL PRODUCTO A MERADOLIBRE: {response.status_code} - {response.json()}"""
        message = call_ai(usr_prompt, PROMPT_FAILED)
        item_metadata = {'status': 'no publicado','reason': message}
        enviar_mensaje_whapi(TOKEN_WHAPI,PHONES, message)
        load_failed_status(item_data['id'], item_metadata)
        return

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

def get_category_id(product_name, token):
    """ Generate category ID trough Mercadolibre AI API
        Returns Category ID else None
    """
    response = requests.get("https://api.mercadolibre.com/sites/MLA/domain_discovery/search", 
                            params={"q": product_name, "limit": 1}, 
                            headers={"Authorization": f"Bearer {token}"})
    if response.status_code == 200 and response.json():
        category_id = response.json()[0].get("category_id", None)
        logger.info(f"Category ID Created: {category_id}")
        return category_id
    else:
        logger.info("Failed to create Category ID")
        return None

def set_description(meli_id, description, token):
    """Load Description to Mercadolibre"""
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

def item_reactivate(meli_id, token):
    """
    If item is paused, then try to republish, else dont do anything.
    """
    logger.info(f"Validating current status for item: {meli_id}")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"https://api.mercadolibre.com/items/{meli_id}", 
        headers=headers
    )
    if response.json().get('status') == 'paused':
        logger.info(f"Item {meli_id} is PAUSED. Attempting to re-activate...")
        url = f"https://api.mercadolibre.com/items/{meli_id}"
        payload = {"status": "active"}
        response = requests.put(url, json=payload, headers=headers)
        if response.status_code == 200:
            logger.info(f"Item {meli_id} is now ACTIVE.")
            return
        else:
            logger.error(f"Failed to re-activate item {meli_id}: {response.text}")
            message = f"""Fallo en la etapa de reactivar el item: {meli_id} en Mercadolibre.
                        la respuesta fue\n {response.text}"""
            enviar_mensaje_whapi(TOKEN_WHAPI, PHONES, message)
            return
