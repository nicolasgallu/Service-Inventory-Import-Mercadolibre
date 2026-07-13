import json
import requests
from unidecode import unidecode
from datetime import datetime
from app.utils.logger import logger
from app.service.llm_api import call_deepseek_api
from app.service.notifications import enviar_mensaje_whapi
from app.service.database import update_method, get_method, upsert_method
from app.service.google_pictures import process_images_storage
from app.settings.config import TOKEN_WHAPI, PHONE_INTERNAL, SCHEMA_INVENTORY, SCHEMA_MERCADOLIBRE

ATTRIBUTES_TABLE = 'attributes'
PRODUCTS_TABLE = 'product_catalog_sync'
COSTS_TABLE = 'selling_calculation'

def ai_error_handling(api_response, user_message, item_id):
    logger.info("Improving Error message with AI and updating DB for Customer Visibility.")
    sys_prompt = """
    Your task is to process a JSON error response returned by the Mercado Libre API and 
    produce a cleaner, shorter explanation in Spanish that a non-technical user can easily understand.
    Rules:
    - The response must be formatted as bullet points.
    - Use fewer than 255 characters.
    - Remove any single or double quotation marks.
    """
    user_prompt = api_response.json()
    error_clean = call_deepseek_api(sys_prompt, user_prompt)
    message = f"{user_message}:\n {error_clean}"
    data = {
    'id': {'value': item_id, 'type': 'char'},
    'status': {'value': 'Error.', 'type': 'char'},
    'reason': {'value': error_clean, 'type': 'char'},
    'remedy': {'value': None, 'type': 'char'},
    }
    enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, message)
    update_method(data, SCHEMA_INVENTORY, PRODUCTS_TABLE)



def get_data_for_meli(item_id):
    """"""
    query = {
        'q_columns': [
            'a.id',
            'a.price',
            'a.product_code',
            'a.product_name',
            'a.product_image_b_format_url',
            'a.stock',
            'a.cost',
            'a.description',
            'a.brand',
            'a.model',
            'a.dimentions',
            'a.drive_url',
            'a.product_name_meli',
            'a.meli_id',
            'a.price_mercadolibre',
            'b.category_options',
            'b.category_id',
            'b.currency_id',
            'b.buying_mode',
            'b.condition_type',
            'b.settings'
        ],
        'q_from':f'FROM {SCHEMA_INVENTORY}.{PRODUCTS_TABLE} as a',
        'q_join':[f'LEFT JOIN {SCHEMA_MERCADOLIBRE}.{ATTRIBUTES_TABLE} as b on b.item_id = a.id'],
        'q_where': f'WHERE a.id = {item_id}',
        'q_limit':'LIMIT 1'
    }
    item_data = get_method(query)
    return item_data


def is_valid_gtin(gtin):
    """
    Valida códigos GTIN-8, GTIN-12, GTIN-13 y GTIN-14.
    """
    gtin = str(gtin).strip()

    # Largo válido
    if len(gtin) not in (8, 12, 13, 14):
        return False

    # Solo números
    if not gtin.isdigit():
        return False

    digits = [int(d) for d in gtin]
    check_digit = digits[-1]
    body = digits[:-1]

    # Se recorre de derecha a izquierda alternando pesos 3 y 1
    total = 0
    weight = 3

    for digit in reversed(body):
        total += digit * weight
        weight = 1 if weight == 3 else 3

    calculated = (10 - (total % 10)) % 10

    return calculated == check_digit

def _aux_product_format(item_data):
    """"""
    logger.info("Creating Product Schema for Mercadolibre.")

    item_id = item_data['id']
    public_images = process_images_storage(item_id)
    if public_images == []:
        logger.info("Without images in Folder, using image from Bitcram.")
        public_images = [{'source': item_data["product_image_b_format_url"]}]

    product_name = item_data["product_name_meli"] or item_data["product_name"]
    price = item_data["price_mercadolibre"] or item_data["price"]
    settings = json.loads(item_data['settings'])

    value_added_tax_ids = {
        "0 %": "48405907",
        "10.5 %": "48405908",
        "21 %": "48405909",
        "27 %": "48405910",
    }
    import_duty_ids = {
        "0 %": "49553239",
        "1 %": "49553240",
        "2.5 %": "49553241",
        "4 %": "49553242",
        "5 %": "49553243",
        "8 %": "49553244",
        "9.5 %": "49553245",
        "10 %": "49553246",
        "14 %": "49553247",
        "15 %": "49553248",
        "18 %": "49553249",
        "19 %": "49553250",
        "20 %": "49553251",
        "23 %": "49553252",
        "25 %": "49553253",
        "26 %": "49553254",
        "70 %": "49553255"
    }
    
    item_format = {
        "title": product_name,
        "category_id": item_data['category_id'], 
        "price": str(price), 
        "currency_id": 'ARS', 
        "available_quantity": item_data['stock'],
        "buying_mode": item_data['buying_mode'], 
        "condition": item_data['condition_type'],
        "pictures": public_images, 
        "attributes": [
            {"id": "BRAND", "value_name": item_data['brand']},
            {"id": "MODEL", "value_name": item_data['model']},
        ],
        "shipping": {},
        "sale_terms": []
    }

    if not is_valid_gtin(item_data['product_code']):
        product_code = {
            "id": "SELLER_SKU",
            "value_name": item_data['product_code']
        }   

        attr_gtin = {
            "id": "GTIN",
            "value_name": "N/A"
        }   

        gtin_reason = {
            "id": "EMPTY_GTIN_REASON",
            "value_id": "17055160"
        }   

        item_format['attributes'].append(product_code)
        item_format['attributes'].append(attr_gtin)
        item_format['attributes'].append(gtin_reason)   

    else:
        product_code = {
            "id": "GTIN",
            "value_name": item_data['product_code']
        }   

        item_format['attributes'].append(product_code)

    for setting_dict in settings:
        for setting in setting_dict:
            if setting == 'attributes':
                for v in setting_dict[setting]:
                    if v["id"] == "VALUE_ADDED_TAX":
                        item_format["attributes"].append({
                            "id": "VALUE_ADDED_TAX",
                            "value_id": value_added_tax_ids.get(v["user_input_value"]),
                            "value_name": v["user_input_value"],
                        })
                    elif v["id"] == "IMPORT_DUTY":
                        item_format["attributes"].append({
                            "id": "IMPORT_DUTY",
                            "value_id": import_duty_ids.get(v["user_input_value"]),
                            "value_name": v["user_input_value"],
                        })
                    else:
                        item_format["attributes"].append({
                            "id": v["id"],
                            "value_name": v["user_input_value"],
                        })

            if setting == 'sale_terms':
                [item_format['sale_terms'].append({"id": v['id'], "value_name": v['user_input_value']}) for v in setting_dict[setting]]

            elif setting == 'shipping':
                [item_format["shipping"].update({v["id"]: v["user_input_value"]}) for v in setting_dict[setting]]
            
            elif setting == 'listing':
                item_format['listing_type_id'] = [v.get('user_input_value') for v in setting_dict[setting]][0]
    
    return item_format


def _generate_category_options(item_id, product_name, token):
    """ Generate category ID trough Mercadolibre API.
        If Categoty already exists then returns None.
    """
    logger.info("Generating Category Options")
    response = requests.get("https://api.mercadolibre.com/sites/MLA/domain_discovery/search", 
        params={"q": product_name, "limit": 6}, 
        headers={"Authorization": f"Bearer {token}"}
    )
    if response.status_code == 200:
        value = unidecode(json.dumps(response.json(), ensure_ascii=False).replace("'","").replace("\\n",""))
        data = {
            'item_id': {'value': item_id, 'type': 'char'},
            'category_options': {'value': value , 'type': 'json'},
            'updated_at': {'value': datetime.now(), 'type': 'datetime'}
        }
        update_method(data, SCHEMA_MERCADOLIBRE, ATTRIBUTES_TABLE)
    else:
        logger.error(f"Failed to create Category Options {response.text}")
    
    return


def _settings_builder(item_id, category_id, price, token):
    """Return all required attributes giving the category"""

    logger.info("Running Settings Builder")
    HEADER = {"Authorization": f"Bearer {token}"}    
    INTERNAL_AVOID_REQMNT = ['BRAND', 'MODEL', 'GTIN', 'EMPTY_GTIN_REASON']

    default_settings = {
        "WARRANTY_TIME": "30 dias",
        "WARRANTY_TYPE": "Garantia del vendedor",
        "VALUE_ADDED_TAX": "21 %",
        "IMPORT_DUTY": "0 %",
        "UNITS_PER_PACK": "1",
        "VOLUME_CAPACITY": "1 mL",
        "MODE": "me2",
        "LOCAL_PICK_UP": "True",
        "FREE_SHIPPING": "False",
        "LISTING_TYPE": "gold_special",
        "LOGISTIC_TYPE": "drop_off",
    }

    settings_list = [{'attributes':[]}, {'shipping':[]}, {'sale_terms':[]}, {'listing':[]}]
    
    for idx ,setting_dict in enumerate(settings_list):
        for setting in setting_dict:
            logger.info(f"Building {setting}..")
            if setting == 'attributes':
                response = requests.get(f"https://api.mercadolibre.com/categories/{category_id}/{setting}", headers=HEADER).json()

            elif setting == 'sale_terms':
                response = requests.get(f"https://api.mercadolibre.com/categories/{category_id}/{setting}", headers=HEADER).json()

            elif setting == 'shipping':
                url = f"https://api.mercadolibre.com/categories/{category_id}/shipping_preferences"
                response = requests.get(url, headers=HEADER).json()
                var1 = {
                    'id': 'MODE', 
                    'name': 'Metodo de Envio',
                    'values':[{'name':[log.get('mode') for log in response.get('logistics')]}],
                    'value_type': 'list',
                    'value_max_lenght': '255'
                }
                var2 = {
                    'id': 'LOCAL_PICK_UP', 
                    'name': 'Buscar en Local',
                    'values':[{'name':['True','False']}],
                    'value_type': 'list',
                    'value_max_lenght': '5'
                }
                var3 = {
                    'id': 'FREE_SHIPPING', 
                    'name': 'Envio Gratis',
                    'values':[{'name':['True','False']}],
                    'value_type': 'list',
                    'value_max_lenght': '5'
                }
                var4 = {
                    'id': 'LOGISTIC_TYPE', 
                    'name': 'Tipo de Logistica',
                    'values':[{'name':['fulfillment','cross_docking','self_service','drop_off','custom']}],
                    'value_type': 'list',
                    'value_max_lenght': '20'
                }
                response = [var1, var2, var3, var4]

            elif setting == 'listing':
                response = requests.get(f"https://api.mercadolibre.com/sites/MLA/listing_prices?price={price}&category_id={category_id}", headers=HEADER).json()
                listing_data = [{
                    "id": data.get('listing_type_id'),
                    "name": data.get('listing_type_name'),
                    "sale_fee_amount": data.get('sale_fee_amount'),
                    "sale_fee_details": data.get('sale_fee_details'),
                    "listing_fee_amount": data.get('listing_fee_amount'),
                    "listing_fee_details": data.get('listing_fee_details'),
                } for data in response]
                response = [{
                    'id': 'LISTING_TYPE', 
                    'name': 'Campaña de Cuotas',
                    'values':[{'name':listing_data}],
                    'value_type': 'list',
                    'value_max_lenght': '255'
                }]
                
            for i in response:
                id = i.get('id')
                if setting == 'attributes':
                    bool_att_req = i.get('tags').get('required', i.get('tags').get('conditional_required'))

                if (bool_att_req == True and id not in INTERNAL_AVOID_REQMNT) or (
                    setting == 'sale_terms' and id in ['WARRANTY_TYPE', 'WARRANTY_TIME']) or (
                    setting == 'listing' or setting == 'shipping'
                    ): 
                    values = {
                        'id': id,
                        'name': i.get('name'),
                        'value_examples': [val.get('name') for val in i.get('values')] if i.get('values') else '',
                        'value_max_lenght': i.get('value_max_length', ''),
                        'value_type': i.get('value_type', ''),
                        'condition': 'Restricted Input' if i.get('value_type').lower() == 'list' else 'Free Input',
                        'user_input_value': default_settings.get(id, '')
                    }
                    settings_list[idx][setting] += [values]
                    logger.info(f"{setting}: {id} added to json.")

    data = {'item_id': {'value': item_id, 'type': 'char'}}
    data['settings'] = {
        'value': unidecode(json.dumps(settings_list, ensure_ascii=False).replace("'","").replace("\\n","")
        ), 'type': 'json'
    }
    data['updated_at'] = {'value': datetime.now(), 'type': 'datetime'}
    update_method(data, SCHEMA_MERCADOLIBRE, ATTRIBUTES_TABLE)


def prepublish_product(item_id, token):
    """"""
    logger.info("Running Pre-Publish Action on Mercadolibre")
    
    item_data = get_data_for_meli(item_id)
    product_name = item_data["product_name_meli"] or item_data["product_name"]
    price = item_data["price_mercadolibre"] or item_data["price"]
    category_options = item_data['category_options']
    category_id = item_data['category_id']
    settings = item_data['settings']
    if category_options is None:
        _generate_category_options(item_id, product_name, token)

    elif category_id is not None and settings is None:
        _settings_builder(item_id, category_id, price, token)
    
    elif category_id is None and category_options is not None:
        data = {
        'item_id': {
            'value': item_id, 
            'type': 'char'
            },
        'settings': {
            'value': json.dumps([{'Error': 'Es necesario seleccionar una categoria.'}]), 
            'type': 'json'
            },
        'updated_at': {
                'value': datetime.now(), 
                'type': 'datetime'
            }
        }
        update_method(data, SCHEMA_MERCADOLIBRE, ATTRIBUTES_TABLE)
    
    return


def publish_item(item_id, token):
    """publish the item with a second try option"""

    logger.info("Running Publish Action on Mercadolibre")
    item_data = get_data_for_meli(item_id)
    logger.info("Step 1: Checking if product is already publish.")
    if item_data['meli_id']:
        logger.warning(f"""Item: {item_id} already exists in mercadolibre 
            under this ID: {item_data['meli_id']}, nothing to do.""")
        return
    
    logger.info("Step 2: Attempting to publish the product in mercadolibre.")
    item_format = _aux_product_format(item_data)
    response = requests.post("https://api.mercadolibre.com/items", 
                    json=item_format,
                    headers={"Authorization": f"Bearer {token}"})
        
    if response.status_code < 300:
        logger.info("Publishing Item Done Succesfully.")
        meli_id = response.json().get('id')
        permalink = response.json().get('permalink')
        _set_description(meli_id, item_data["description"], token)
        data = {
        'id': {
            'value': item_id, 
            'type': 'char'
            },
        'meli_id': {
            'value': meli_id, 
            'type': 'char'
            },
        'permalink': {
            'value': permalink, 
            'type': 'char'
            },
        'status': {
            'value': 'Procesando..', 
            'type': 'char'
            },
        'reason': {
            'value': 'Procesando..', 
            'type': 'char'
            },
        'remedy': {
            'value': 'Procesando..', 
            'type': 'char'
            },
        }
        update_method(data, SCHEMA_INVENTORY, PRODUCTS_TABLE)
    else:
        user_message = f"Error while publishing item: {item_id}"
        logger.info(response.json())
        ai_error_handling(response, user_message, item_id)
    return



def update_item(item_id, token):
    """Update MercadoLibre item"""
    
    logger.info("Running Update Action on Mercadolibre")
    item_data = get_data_for_meli(item_id)
    meli_id = item_data['meli_id']
    if meli_id is None or meli_id == '':
        logger.error(f"Item: {item_data['id']} is not published, nothing to update.")
        return
    
    url = f"https://api.mercadolibre.com/items/{meli_id}"
    headers = {"Authorization": f"Bearer {token}"}

    def _item_status():
        logger.info(f"Validating Status of the Product : {meli_id}.")
        response = requests.get(url=url, headers=headers)
        if response.status_code <300:
            response = response.json()
            sold_quantity = response.get("sold_quantity")
            status = response.get('status')
            sub_status = next(iter(response.get('sub_status') or []), 'good')
            logger.info(f"Status output: {status} : {sub_status}")
            return status, sub_status, sold_quantity

    status, sub_status, sold_quantity = _item_status()
    if status == 'under_review' and sub_status == 'forbidden':
        logger.info(f"Product in Forbidden status: {meli_id}, we are gonna delete and publish again.")
        delete_item(item_data, token)
        publish_item(item_data, token)
    
    else:
        item_format = _aux_product_format(item_data)

        listing_type_id = item_format.get('listing_type_id')
        del item_format['category_id']
        del item_format['currency_id']
        del item_format['condition']
        del item_format['attributes']
        del item_format['buying_mode']        
        del item_format['shipping']
        del item_format['listing_type_id']

        if sold_quantity > 0:
            del item_format["title"]

        def _aux_update_listing():
            data = {"id": listing_type_id}
            response = requests.put(f"{url}/listing_type", data=data, headers=headers)
            if response.status_code < 300:
                logger.info("Listing Type Update Done.")

        def _aux_reactivate_item():
            """If item is paused, then try to reactive, else do nothing."""
            if status == 'paused':
                logger.info(f"Item {meli_id} is PAUSED. Attempting to re-activate...")
                data = {"status": "active"}
                response = requests.put(url=url, headers=headers, json=data)
                if response.status_code < 300:
                    logger.info("Reactivate Done.")
                else:
                    user_message = f"Error while reactivating product: {meli_id}"
                    ai_error_handling(response, user_message, item_id)
    
        def _aux_update_item():
            response = requests.put(url=url, json=item_format, headers=headers)
            if response.status_code < 300:
                logger.info("General Update Done.")
                _set_description(meli_id, item_data['description'], token, update=True)
                _aux_update_listing()
                _aux_reactivate_item()
            else:
                user_message = f"Error while updating product: {meli_id}"
                logger.info(response.json())
                ai_error_handling(response, user_message, item_id)
        
        _aux_update_item()

    return

 

def pause_item(item_id, token):
    """Changes item status to paused in Mercado Libre"""

    logger.info("Running Pause Action on Mercadolibre")
    item_data = get_data_for_meli(item_id)
    meli_id = item_data['meli_id'] 

    if meli_id is None:
        logger.error(f"Product: {item_data['id']} is not published, nothing to update.")
        return

    logger.info(f"Attempting to pause product: {meli_id}")
    response = requests.put(f"https://api.mercadolibre.com/items/{meli_id}", 
            json={"status": "paused"},
            headers={ "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    )
    if response.status_code == 200:
        logger.info(f"Product: {meli_id} successfully paused.")
    else:
        logger.error(f"""
            Failed to pause item {meli_id}.\n 
            Status: {response.status_code}.\n 
            Error:\n {response.json()}"""
        )
        enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, response.json())
    return


def delete_item(item_id, token):
    """"""

    logger.info("Running Delete Action on Mercadolibre")
    item_data = get_data_for_meli(item_id)
    meli_id = item_data['meli_id'] 

    if meli_id is None:
        logger.error(f"Product: {item_id} is not published, nothing to delete.")
        return
    
    url = f"https://api.mercadolibre.com/items/{meli_id}"
    headers = { "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    var_closed = {"status": "closed"}
    var_deleted = {"deleted": "true"}
    requests.put(url=url, json=var_closed, headers=headers)
    requests.put(url=url, json=var_deleted, headers=headers)

    data = {
        'id': {'value': item_id, 'type': 'char'},
        'status': {'value': None, 'type': 'char'},
        'reason': {'value': None, 'type': 'char'},
        'remedy': {'value': None, 'type': 'char'},
        'permalink': {'value': None, 'type': 'char'},
        'meli_id': {'value': None, 'type': 'char'},
        }
    update_method(data, SCHEMA_INVENTORY, PRODUCTS_TABLE)
    return

    
def _set_description(meli_id, description, token, update=False):
    """Load Description to Mercadolibre"""
    logger.info("Checking if description exists.")
    if description:
        logger.info(f"Loading Description for product: {meli_id}")
        url = f"https://api.mercadolibre.com/items/{meli_id}/description"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {"plain_text": description}
        if update == True:
            response = requests.put(url, json=payload, headers=headers)
        else:
            response = requests.post(url, json=payload, headers=headers)
        if response.status_code <300:
            logger.info(f"Description loaded for product: {meli_id}")
        else:
            logger.error(f"Failed to load description for product {meli_id}: {response.status_code} - {response.text}")
    else:
        logger.info("Description dont exists, nothing to do.")


def calculate_cost(item_data:dict, user_id:str, token:str):
    """Calculate the cost for selling in mercadolibre."""

    logger.info("Running Cost Calculation Action")
    header = {'Authorization': f'Bearer {token}'}

    all_settings_groups = json.loads(item_data.get("settings"))
    for settings_group in all_settings_groups:
        for section_name in settings_group:
            if section_name == "shipping":
                for variable in settings_group[section_name]:
                    if variable.get('id') == 'FREE_SHIPPING':
                        free_shipping = variable.get('user_input_value')
                    if variable.get('id') == 'MODE':
                        shipping_mode = variable.get('user_input_value')
                    if variable.get('id') == 'LOGISTIC_TYPE':
                        logistic_type = variable.get('user_input_value')

            elif section_name == "listing":
                for variable in settings_group[section_name]:
                    if variable.get('id') == 'LISTING_TYPE':
                        listing_type = variable.get('user_input_value')
    
    item_id = item_data.get('id')
    condition_type = item_data.get('condition_type')
    category_id = item_data.get('category_id')
    currency = item_data.get('currency_id')
    dimentions = item_data.get('dimentions')
    billable_weight = 5828
    price = item_data.get("price_mercadolibre") if item_data.get("price_mercadolibre") else item_data.get("price")
    

    logger.info("Step 1. Calculating Selling Cost (without shipping)")
    url = (
        f"https://api.mercadolibre.com/sites/MLA/listing_prices?"
        f"category_id={category_id}&price={price}&cy_id={currency}&"
        f"logistic_type={logistic_type}&shipping_modes={shipping_mode}&"
        f"listing_type_id={listing_type}&billable_weight={billable_weight}&"
    )    
    response = requests.get(url=url,headers=header)
    if response.status_code > 300:
        user_message = f"Error while calculating cost for product: {item_id}: {response.json()}"
        logger.error(user_message)
        return
    
    response = response.json()
    cost_detail = {
        'item_id':{'value': item_id, 'type':'char'},
        'sale_fee_amount':{'value': response['sale_fee_amount'], 'type':'float'}, 
        'fixed_fee':{'value':  response['sale_fee_details']['fixed_fee'], 'type':'float'}, 
        'financing_add_on_fee':{'value':  response['sale_fee_details']['financing_add_on_fee'], 'type':'float'}, 
        'meli_percentage_fee':{'value':  response['sale_fee_details']['meli_percentage_fee'], 'type':'float'},
        'percentage_fee':{'value':  response['sale_fee_details']['percentage_fee'], 'type':'float'},
        'gross_amount':{'value':  response['sale_fee_details']['gross_amount'], 'type':'float'},
        'listing_fixed_fee':{'value': response['listing_fee_details']['fixed_fee'], 'type':'float'}, 
        'listing_gross_amount':{'value': response['listing_fee_details']['gross_amount'], 'type':'float'}, 
    }

    logger.info("Step 2. Calculating Shipping Cost")
    url = (
        f"https://api.mercadolibre.com/users/{user_id}/"
        f"shipping_options/free?dimensions={dimentions}&"
        f"verbose=true&item_price={price}&category_id={category_id}&"
        f"listing_type_id={listing_type}&mode={shipping_mode}&"
        f"condition={condition_type}&logistic_type={logistic_type}&free_shipping={free_shipping}"
    )
    response = requests.get(url=url, headers=header)
    if response.status_code > 300:
        user_message = f"Error while calculating cost for product: {item_id}: {response.json()}"
        logger.error(user_message)
        return
    
    response = response.json()
    cost_detail['ship_cost_amount'] = {'value': response['coverage']['all_country']['list_cost'], 'type': 'float'}
    cost_detail['ship_discount'] = {'value': response['coverage']['all_country']['discount']['rate'], 'type': 'float'}
    cost_detail['ship_cost_full_amount'] = {'value': response['coverage']['all_country']['discount']['promoted_amount'], 'type': 'float'}
    total_selling_cost = cost_detail.get('ship_cost_amount').get('value') + cost_detail.get('sale_fee_amount').get('value')
    cost_detail['total_selling_cost'] = {'value': total_selling_cost, 'type': 'float'}
    
    upsert_method(cost_detail, SCHEMA_MERCADOLIBRE, COSTS_TABLE )
    return