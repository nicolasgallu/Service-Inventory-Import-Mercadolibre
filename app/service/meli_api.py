import json
import requests
from unidecode import unidecode
from datetime import datetime
from app.utils.logger import logger
from app.service.llm_api import call_deepseek_api
from app.service.notifications import enviar_mensaje_whapi
from app.service.database import update_method, get_method, upsert_method
from app.settings.config import TOKEN_WHAPI, PHONE_INTERNAL

schema_inventory = 'app_import'
schema_mercadolibre = 'mercadolibre'
table = 'attributes'

def ai_error_handling(api_response, user_message, item_id):
    table = 'product_catalog_sync'
    sys_prompt = """Tu tarea es procesar una respuesta json
    de un error retornado por la API de MercadoLibre, y devolver, en español un 
    formato mas limpio y corto para que el usuario no-tech pueda entenderlo mejor.
    Rule: Usa menos de 255 caracteres.
    """
    logger.info("Improving Error message with AI and sending.")
    user_prompt = api_response.json()
    error_clean = call_deepseek_api(sys_prompt, user_prompt)
    message = f"{user_message}:\n {error_clean}"
    
    data = {
    'id': {
        'value': item_id, 
        'type': 'char'
        },
    'status': {
        'value': 'Error.', 
        'type': 'char'
        },
    'reason': {
        'value': error_clean, 
        'type': 'char'
        },
    'remedy': {
        'value': None, 
        'type': 'null'
        },
    }
    
    logger.error(message)
    enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, message)
    update_method(data, schema_inventory ,table)


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
            'b.listing_type_id',
            'b.free_shipping',
            'b.mode_shipping',
            'b.volume_capacity',
            'b.category_id',
            'b.currency_id',
            'b.buying_mode',
            'b.condition_type',
            'b.value_added_tax',
            'b.import_duty',
            'b.units_per_pack',
            'b.local_pick_up',
            'b.warranty_type',
            'b.warranty_time',
            'b.logistic_type',
            'b.category_options'
        ],
        'q_from':f'FROM {schema_inventory}.product_catalog_sync as a',
        'q_join':f'LEFT JOIN {schema_mercadolibre}.attributes as b on b.item_id = a.id',
        'q_where': f'WHERE a.id = {item_id}',
        'q_limit':'LIMIT 1'
    }
    item_data = get_method(query)
    return item_data


def _aux_product_format(item_data, public_images):
    """"""
    logger.info("Creating Product Format.")
    if item_data["product_name_meli"]: 
        product_name = item_data["product_name_meli"]
    else:
        product_name = item_data["product_name"]

    if item_data.get("price_mercadolibre"):
        price = item_data.get("price_mercadolibre")
    else:
        price = item_data.get("price")

    item_format = {
        "title": product_name, 
        "category_id": item_data.get('category_id'), 
        "price": str(price), 
        "currency_id": 'ARS', 
        "available_quantity": item_data.get('stock'),
        "buying_mode": item_data.get('buying_mode'), 
        "condition": item_data.get('condition_type'),
        "listing_type_id": item_data.get('listing_type_id'),
        "pictures": public_images, 
        "attributes": [
            {"id": "BRAND", "value_name": item_data.get('brand')},
            {"id": "MODEL", "value_name": item_data.get('model')},
            {"id": "VALUE_ADDED_TAX", "value_id": str(item_data.get('value_added_tax'))},
            {"id": "IMPORT_DUTY", "value_id": str(item_data.get('import_duty'))},
            {"id": "UNITS_PER_PACK", "value_name": item_data.get('units_per_pack')}
        ],
        "shipping": { 
            "mode": item_data.get('mode_shipping'), 
            "local_pick_up": item_data.get('local_pick_up'),
            "free_shipping": item_data.get('free_shipping')
        },
        "sale_terms": [
            {"id": "WARRANTY_TYPE", "value_name": item_data.get('warranty_type')}, 
            {"id": "WARRANTY_TIME", "value_name": item_data.get('warranty_time')},
        ]
    }

    if len(item_data['product_code']) not in [8,12,13,14]:
        product_code = {
            "id": "SELLER_SKU", 
            "value_name": item_data['product_code']}
        attr_gtin = {
            "id": "GTIN", 
            "value_name": "N/A"}
        gtin_reason = {
            "id": "EMPTY_GTIN_REASON", 
            "value_id": "17055160"}
        item_format['attributes'].append(product_code)
        item_format['attributes'].append(attr_gtin)
        item_format['attributes'].append(gtin_reason)
    else:
        product_code = {"id": "GTIN", "value_name": item_data['product_code']}
        item_format['attributes'].append(product_code)
    
    volume_cap = item_data.get('volume_capacity')
    if volume_cap:
        volume_cap = {
            "id": "VOLUME_CAPACITY", 
            "value_name": str(volume_cap) + ' mL'
        }
        item_format['attributes'].append(volume_cap)

    return item_format


def _generate_category_options(item_id, product_name, token):
    """ Generate category ID trough Mercadolibre API.
        If Categoty already exists then returns None.
    """
    response = requests.get("https://api.mercadolibre.com/sites/MLA/domain_discovery/search", 
        params={
            "q": product_name, 
            "limit": 6}, 
        headers={
            "Authorization": f"Bearer {token}"}
    )

    if response.status_code == 200:

        logger.info(f"Category Options Generated")
        data = {
            'item_id': {
                'value': item_id, 
                'type': 'char'
            },
            'category_id': {
                'value': json.dumps(response.json()), 
                'type': 'json'
            },
            'updated_at': {
                'value': datetime.now(), 
                'type': 'datetime'
            }
        }
        update_method(data, schema_mercadolibre, table)  
    else:
        logger.error(f"Failed to create Category Options {response.text}")
        return None


def _get_attributes(item_id, category_id, token):
    """Return all required attributes giving the category"""
    internal_requirements = [
        'volume_capacity_required',
        'units_per_pack_required',
        'value_added_tax_required',
        'import_duty_required',
        'empty_gtin_reason_required'
    ]
    internal_avoided_req = [
        'brand_required',
        'model_required',
        'gtin_required'
    ]
    logger.info("Reading attributes requirements.")
    response = requests.get(f"https://api.mercadolibre.com/categories/{category_id}/attributes",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )
    if response.status_code == 200:
        req_attributes = response.json()
        data = {'item_id': {'value': item_id, 'type': 'char'}}
        not_mapped_att = []
        for i in req_attributes:
            attribute_name = i.get('id').lower() + "_required"
            tag_required = i.get('tags').get('required', i.get('tags').get('conditional_required', None))
            if tag_required == True:
                if attribute_name in (internal_requirements):
                    logger.info(f"Attribute {attribute_name} is required.")
                    data[attribute_name] = {'value': True, 'type': 'boolean'}
                elif attribute_name not in internal_avoided_req: 
                    logger.info(f"New Attribute {attribute_name} not mapped.")
                    not_mapped_att += [i]
            else: 
                continue
        if len(data.keys()) > 1:
            data['not_mapped_attributes'] = {
                'value': unidecode(
                    json.dumps(
                        not_mapped_att, 
                        ensure_ascii=False
                        )
                        .replace("'","")
                        .replace("\\n","")
                ), 'type': 'json'
            }
            data['updated_at'] = {
                'value': datetime.now(), 
                'type': 'datetime'}
            update_method(data, schema_mercadolibre, table)      


def _get_allowed_values(item_id, category_id, price, token):
    """Get allowed values for Sale Terms, Shipping and Listing Prices"""
    headers = {"Authorization": f"Bearer {token}"}
    
    url_terms = f"https://api.mercadolibre.com/categories/{category_id}/sale_terms"
    res_terms = requests.get(url_terms, headers=headers).json()
    warranty_data = {}
    for term in res_terms:
        if term['id'] in ['WARRANTY_TYPE', 'WARRANTY_TIME']:
            val = [v.get('name') for v in term.get('values', [])] if term.get('value_type') == 'list' else f"Entrada libre ({term.get('value_type')})"
            warranty_data[term['id']] = val

    url_ship = f"https://api.mercadolibre.com/categories/{category_id}/shipping_preferences"
    res_ship = requests.get(url_ship, headers=headers).json()
    shipping_data = {
        "modos": [log.get('mode') for log in res_ship.get('logistics', [])],
        "metodos": [m.get('name') for m in res_ship.get('methods', [])]
    }

    url_prices = f"https://api.mercadolibre.com/sites/MLA/listing_prices?price={price}&category_id={category_id}"
    res_prices = requests.get(url_prices, headers=headers).json()
    prices_data = [
        {
            "id": p.get('listing_type_id'),
            "nombre": p.get('listing_type_name'),
            "comision_fija": p.get('sale_fee_amount'),
            "porcentaje_comision": f"{p.get('listing_fee_details', {}).get('percentage')}%"
        } 
        for p in res_prices
    ]

    category_metadata = {
        "category_id": category_id,
        "settings": {
            "warranty": warranty_data,
            "shipping": shipping_data,
            "listing_options": prices_data
        }
    }
    data = {
        'item_id': {
            'value': item_id, 
            'type': 'char'
            }
        }
    data['allowed_options'] = {
        'value': json.dumps(category_metadata, ensure_ascii=False), 
        'type': 'json'}
    data['updated_at'] = {
        'value': datetime.now(), 
        'type': 'datetime'}
    update_method(data, schema_mercadolibre, table)


def prepublish_product(item_data:dict, token:str):
    """"""
    logger.info("Runing Prepublish Examination")
    item_id = item_data.get('id')
    product_name = item_data.get('product_name')
    price =  item_data.get("price_mercadolibre") if item_data.get("price_mercadolibre") else item_data.get("price")
    category_options = item_data.get('category_options')
    if category_options is None:
        _generate_category_options(item_id, product_name, token)
    else:
        category_id = item_data.get('category_id')
        _get_attributes(item_id, category_id, token)
        _get_allowed_values(item_id, category_id, price, token)


def publish_item(item_data, public_images, token):
    """publish the item with a second try option"""
    table = 'product_catalog_sync'

    item_id = item_data.get('id')
    logger.info("Step 1: Checking if product is already publish.")
    if item_data['meli_id']:
        logger.warning(f"""Item: {item_id} already exists in mercadolibre 
            under this ID: {item_data['meli_id']}, nothing to do.""")
        return
    
    logger.info("Step 2: Attempting to publish the product in mercadolibre.")
    item_format = _aux_product_format(item_data, public_images)
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
        update_method(data, schema_inventory, table)
        return
    
    else:
        user_message = f"Error while publishing item: {item_id}"
        ai_error_handling(response, user_message, item_id)
        return



def update_item(item_id, item_data, public_images, token):
    """Update MercadoLibre item"""

    logger.info("Updating product in mercadolibre")
    meli_id = item_data.get('meli_id')
    
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
        publish_item(item_data, public_images, token)
        return
    
    else:
        item_format = _aux_product_format(item_data, public_images)

        del item_format['category_id']
        del item_format['currency_id']
        del item_format['condition']
        del item_format['attributes']
        listing_type_id = item_format.get('listing_type_id')
        del item_format['listing_type_id']

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
                return
            else:
                user_message = f"Error while updating product: {meli_id}"
                ai_error_handling(response, user_message, item_id)

        if sold_quantity > 0:
            logger.info(f"Product: {meli_id} has one sell or more.")
            del item_format["title"]
            _aux_update_item()
        else:
            logger.info(f"Product: {meli_id} has no sells.")
            _aux_update_item()

 

        
def pause_item(item_data, token):
    """Changes item status to paused in Mercado Libre"""
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
        return
    else:
        logger.error(f"""
            Failed to pause item {meli_id}.\n 
            Status: {response.status_code}.\n 
            Error:\n {response.json()}"""
        )
        enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, response.json())
        return


def delete_item(item_data, token): 
    """"""
    meli_id = item_data['meli_id'] 
    item_id = item_data['id']
    table = 'product_catalog_sync'

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
        'id': {
            'value': item_id, 
            'type': 'char'
            },
        'status': {
            'value': None, 
            'type': 'null'
            },
        'reason': {
            'value': None, 
            'type': 'null'
            },
        'remedy': {
            'value': None, 
            'type': 'null'
            },
        'permalink': {
            'value': None, 
            'type': 'null'
            },
        'meli_id': {
            'value': None, 
            'type': 'null'
            },
        }
    update_method(data, schema_inventory, table)

    
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
    
    item_id = item_data.get('id')
    condition_type = item_data.get('condition_type')
    category_id = item_data.get('category_id')
    currency = item_data.get('currency_id')
    dimentions = item_data.get('dimentions')
    shipping_mode = item_data.get('mode_shipping')
    listing_type = item_data.get('listing_type_id')
    free_shipping = item_data.get('free_shipping')
    logistic_type = item_data.get('logistic_type')
    billable_weight = 5828
    price = item_data.get("price_mercadolibre") if item_data.get("price_mercadolibre") else item_data.get("price")
    

    header = {'Authorization': f'Bearer {token}'}

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
        'sale_fee_amount':{'value': response['sale_fee_amount'], 'type':'signed'}, 
        'fixed_fee':{'value':  response['sale_fee_details']['fixed_fee'], 'type':'signed'}, 
        'financing_add_on_fee':{'value':  response['sale_fee_details']['financing_add_on_fee'], 'type':'signed'}, 
        'meli_percentage_fee':{'value':  response['sale_fee_details']['meli_percentage_fee'], 'type':'signed'},
        'percentage_fee':{'value':  response['sale_fee_details']['percentage_fee'], 'type':'signed'},
        'gross_amount':{'value':  response['sale_fee_details']['gross_amount'], 'type':'signed'},
        'listing_fixed_fee':{'value': response['listing_fee_details']['fixed_fee'], 'type':'signed'}, 
        'listing_gross_amount':{'value': response['listing_fee_details']['gross_amount'], 'type':'signed'}, 
    }

    logger.info("Step 2. Calculating Shipping Cost")
    url = (
        f"https://api.mercadolibre.com/users/{user_id}/"
        f"shipping_options/free?dimensions={dimentions}&"
        f"verbose=true&item_price={price}&category_id={category_id}&"
        f"listing_type_id={listing_type}&mode={shipping_mode}&"
        f"condition={condition_type}&logistic_type={logistic_type}&free_shipping={free_shipping}")
    response = requests.get(url=url, headers=header)
    if response.status_code > 300:
        user_message = f"Error while calculating cost for product: {item_id}: {response.json()}"
        logger.error(user_message)
        return
    response = response.json()
    cost_detail['ship_cost_amount'] = {'value': response['coverage']['all_country']['list_cost'], 'type': 'signed'}
    cost_detail['ship_discount'] = {'value': response['coverage']['all_country']['discount']['rate'], 'type': 'signed'}
    cost_detail['ship_cost_full_amount'] = {'value': response['coverage']['all_country']['discount']['promoted_amount'], 'type': 'signed'}
    total_selling_cost = cost_detail.get('ship_cost_amount').get('value') + cost_detail.get('sale_fee_amount').get('value')
    cost_detail['total_selling_cost'] = {'value': total_selling_cost, 'type': 'signed'}
    
    table = 'selling_calculation'
    upsert_method(cost_detail, schema_mercadolibre, table )