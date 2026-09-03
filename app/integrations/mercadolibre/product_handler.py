import json
import requests
from app.utils.logger import logger
from app.integrations.core.credentials import get_access_token
from app.db.helpers import get_one, execute, get_all
from app.settings.config import (SCHEMA_INVENTORY, SCHEMA_MERCADOLIBRE)

PRODUCTS_TABLE= 'products'
ATTRIBUTES_TABLE= 'attributes'
PRODUCT_LISTING_TABLE= 'product_listings'
IMAGES_TABLE= 'product_images'
VARIANTS_TABLE= 'variation_listings'


def get_data_for_meli(product_id):
    sql = (
        "SELECT "
        + "a.id, "
        + "a.price, "
        + "a.internal_code, "
        + "a.sku, "
        + "a.gtin, "
        + "a.name, "
        + "a.name_edited, "
        + "a.stock, "
        + "a.cost, "
        + "a.description, "
        + "a.brand, "
        + "a.model, "
        + "a.dimensions, "
        + "a.drive_url, "
        + "b.id AS product_listing_id, "
        + "b.meli_id, "
        + "b.price AS price_meli, "
        + "c.id AS attribute_id, "
        + "c.category_options, "
        + "c.category_id, "
        + "c.currency_id, "
        + "c.buying_mode, "
        + "c.condition_type, "
        + "c.settings "
        + "FROM " + SCHEMA_INVENTORY + "." + PRODUCTS_TABLE + " AS a "
        + "LEFT JOIN " + SCHEMA_MERCADOLIBRE + "." + PRODUCT_LISTING_TABLE + " AS b ON b.product_id = a.id "
        + "LEFT JOIN " + SCHEMA_MERCADOLIBRE + "." + ATTRIBUTES_TABLE + " AS c ON c.product_listing_id = b.id "
        + "WHERE a.id = :product_id "
    )
    row = get_one(sql, {"product_id": product_id,})
    return row


def get_product_images(product_id):
    sql = (
        "SELECT "
        + "url "
        + "FROM " + SCHEMA_INVENTORY + "." + IMAGES_TABLE + " " 
        + "WHERE product_id = :product_id "
    )
    try:
        return get_all(sql, {"product_id": product_id,})
    except LookupError:
        return []


def get_product_variants(product_id):
    sql = (
        "SELECT "
        + "id "
        + "FROM " + SCHEMA_MERCADOLIBRE + "." + VARIANTS_TABLE + " " 
        + "WHERE product_listing_id = :product_id "
    )
    try:
        return get_one(sql, {"product_id": product_id,})
    except LookupError:
        return {}




def _update_record(id, data, table):
    fields = []
    params = {"id": id}
    for field, value in data.items():
        if value is not None:
            fields.append(f"{field} = :{field}")
            params[field] = value
    if not fields:
        return
    
    sql = (
        "UPDATE " + SCHEMA_MERCADOLIBRE + "." + table
        + " SET " + ", ".join(fields)
        + " WHERE id = :id"
    )
    rowcount = execute(sql, params)
    logger.info("Rows Affected: ")
    logger.info(rowcount)


def _delete_record(id, table):
    logger.info(f"Deleting: {id}")
    sql = (
        "DELETE FROM " + SCHEMA_MERCADOLIBRE + "." + table
        + " WHERE id = :id"
    )
    rowcount = execute(sql, {'id': id})
    logger.info("Rows Affected: ")
    logger.info(rowcount)




def _aux_product_format(item_data):
    """"""
    logger.info("Creating Product Schema for Mercadolibre.")

    public_images=[]
        
    if public_images == []:
        logger.info("Without images in Folder, using images from DB.")
        product_id = item_data['id']
        public_images = get_product_images(product_id)
        public_images = [{'source': image["url"]} for image in public_images[:5]]


    product_name = item_data["name_edited"] or item_data["name"]
    price = item_data["price_meli"] or item_data["price"]
    settings = json.loads(item_data['settings'] or '[]')

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
        "family_name": product_name,
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

    if item_data['gtin'] is None:
        product_code = { "id": "SELLER_SKU", "value_name": item_data['sku']}   
        attr_gtin = { "id": "GTIN", "value_name": "N/A"}   
        gtin_reason = { "id": "EMPTY_GTIN_REASON", "value_id": "17055160"}   
        item_format['attributes'].append(product_code)
        item_format['attributes'].append(attr_gtin)
        item_format['attributes'].append(gtin_reason)

    else:
        product_code = { "id": "GTIN", "value_name": item_data['gtin']}   
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



def _generate_category_options(attrb_id, prod_id, product_names, token):
    """ Generate category ID trough Mercadolibre API.
        If Categoty already exists then returns None.
    """
    logger.info("Generating Category Options")
    for product_name in product_names:
        logger.info(f"Trying Generating Category with name: {product_name}")
        response = requests.get("https://api.mercadolibre.com/sites/MLA/domain_discovery/search", 
            params={"q": product_name, "limit": 6}, 
            headers={"Authorization": f"Bearer {token}"}
        )
        json.dumps(response.json(), ensure_ascii=False)

        category_options = json.dumps(response.json(), ensure_ascii=False)
        if category_options:
            break

    if response.status_code == 200:
        data = {'category_options': category_options}
        _update_record(attrb_id, data, ATTRIBUTES_TABLE)

    else:
        logger.error("Failed to create Category Options.")
        error = json.dumps(response.json(), ensure_ascii=False)
        data = {
        'status': 'Failed to generate category options.', 
        'reason': error, 
        'remedy': 'None', 
        }
        _update_record(prod_id, data, PRODUCT_LISTING_TABLE)
    return



def _settings_builder(attribute_id, category_id, price, token):
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
                response = requests.get(f"https://api.mercadolibre.com/categories/{category_id}/{setting}", headers=HEADER)

                if response.status_code > 300:
                    logger.info("Category Not Valid.")
                    data = json.dumps(response.json(), ensure_ascii=False)
                    data = {'settings': data}
                    _update_record(attribute_id, data, ATTRIBUTES_TABLE)
                    return
                
                else:
                    response = response.json()

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

                if (bool_att_req == True and id not in INTERNAL_AVOID_REQMNT) or id in ["SIZE_GRID_ID", "SIZE_GRID_ROW_ID"] or (
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

    data = json.dumps(settings_list, ensure_ascii=False)
    data = {'settings': data}
    _update_record(attribute_id, data, ATTRIBUTES_TABLE)




def prepublish(payload):
    """"""
    logger.info("Running Pre-Publish Action on Mercadolibre")

    product_id = payload.get('product_id')
    account_id = payload.get('account_id')
    token = get_access_token(account_id).get('access_token')

    product_data = get_data_for_meli(product_id)
    product_names = [product_data["name_edited"], product_data["name"]]
    price = product_data["price_meli"] or product_data["price"]
    category_options = product_data['category_options']
    category_id = product_data['category_id']
    settings = product_data['settings']
    attribute_id = product_data['attribute_id']

    if settings:
        settings = json.loads(settings)
        settings_error_check = [i for i in settings][0].get('Error', False)

    if category_options is None or category_options=='[]':
        _generate_category_options(attribute_id, product_id, product_names, token)

    elif category_id is not None and (settings is None or settings_error_check):
        _settings_builder(attribute_id, category_id, price, token)
    
    elif category_id is None and category_options is not None:
        data = json.dumps([{'Error': 'Para generar los settings es neceasario seleccionar una categoria y correr el evento de Pre-Publish.'}], ensure_ascii=False)
        data = {'settings': data}
        _update_record(attribute_id, data, ATTRIBUTES_TABLE)
    return



def publish(payload):
    """publish the item with a second try option"""

    product_id = payload.get('product_id')
    account_id = payload.get('account_id')
    token = get_access_token(account_id).get('access_token')

    logger.info("Running Publish Action on Mercadolibre")
    item_data = get_data_for_meli(product_id)

    logger.info("Step 1: Checking if product is already publish.")
    if item_data['meli_id']:
        logger.warning(f"""Item: {product_id} already exists in mercadolibre under this ID: {item_data['meli_id']}, nothing to do.""")
        return
    
    logger.info("Step 2: Attempting to publish the product in mercadolibre.")
    item_format = _aux_product_format(item_data)
    response = requests.post("https://api.mercadolibre.com/items", 
                    json=item_format,
                    headers={"Authorization": f"Bearer {token}"})
    product_listing_id = item_data['product_listing_id']
    if response.status_code < 300:
        logger.info("Publishing Item Done Succesfully.")
        meli_id = response.json().get('id')
        permalink = response.json().get('permalink')
        _set_description(meli_id, item_data["description"], token)
        
        data = {
        'meli_id': meli_id, 
        'permalink': permalink, 
        'status': 'Procesando..', 
        'reason': 'Procesando..', 
        'remedy': 'Procesando..', 
        }
        _update_record(product_listing_id, data, PRODUCT_LISTING_TABLE)
        
    else:
        ##MEJORAR ACA VER SI SE PUEDE EXTRAER REMEDY DESDE EL RESPONSE.
        logger.info("Failed to Publish.")
        error = json.dumps([response.json()], ensure_ascii=False)
        data = {
        'status': 'Failed to Publish.', 
        'reason': error, 
        'remedy': 'None', 
        }
        _update_record(product_listing_id, data, PRODUCT_LISTING_TABLE)
    return


def update(payload):
    """Update MercadoLibre item"""
    logger.info("Running Update Action on Mercadolibre")

    product_id = payload.get('product_id')
    account_id = payload.get('account_id')
    

    token = get_access_token(account_id).get('access_token')
    if not token:
        logger.error("No access token found")
        return

    item_data = get_data_for_meli(product_id)
    product_listing_id = item_data.get('product_listing_id')
    meli_id = item_data.get('meli_id')
    if not meli_id:
        logger.error(f"Item {product_id} is not published, nothing to update.")
        return

    # Skip if product has variations (not supported yet)
    if get_product_variants(product_id).get('id'):
        logger.info("Product has variations, skipping update.")
        _update_record(product_listing_id, {'status': 'Failed to Update.', 'reason': 'Product has variations.', 'remedy': 'None'}, PRODUCT_LISTING_TABLE)
        return

    url = f"https://api.mercadolibre.com/items/{meli_id}"
    headers = {"Authorization": f"Bearer {token}"}

    # Get current status and sold quantity
    status, sub_status, sold_quantity = _get_meli_item_status(url, headers, meli_id)
    if status is None:
        _update_record(product_listing_id, {'status': 'Failed to Update.', 'reason': 'Could not retrieve item status', 'remedy': 'None'}, PRODUCT_LISTING_TABLE)
        return

    # If forbidden, delete and republish
    if status == 'under_review' and sub_status == 'forbidden':
        logger.info(f"Product {meli_id} in Forbidden status, deleting and republishing.")
        delete(payload)
        publish(payload)
        return

    # Build update payload
    item_format = _aux_product_format(item_data)
    listing_type_id = item_format.pop('listing_type_id', None)

    # Remove fields that cannot be updated directly
    for field in ['category_id', 'currency_id', 'condition', 'attributes', 'buying_mode', 'shipping']:
        item_format.pop(field, None)

    # Handle family name: can't update if sold > 0
    if sold_quantity and sold_quantity > 0:
        item_format.pop('family_name', None)
    else:
        if 'family_name' in item_format:
            _update_family_name(url, headers, item_format['family_name'])
            item_format.pop('family_name')

    # Main update
    try:
        response = requests.put(url, json=item_format, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info("General Update Done.")

        # Update description
        if item_data.get('description'):
            _set_description(meli_id, item_data['description'], token, update=True)

        # Update listing type (if possible)
        if listing_type_id:
            _update_listing_type(url, headers, listing_type_id)

        # Reactivate if paused
        if status == 'paused':
            _reactivate_item(url, headers, meli_id, product_listing_id)

        # Update local status
        _update_record(product_listing_id, {'status': 'Updated.','reason': 'None', 'remedy': 'None'}, PRODUCT_LISTING_TABLE)

    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        logger.error(f"Update failed: {error_msg}")
        _update_record(product_listing_id, {'status': 'Failed to Update.', 'reason': error_msg, 'remedy': 'None'}, PRODUCT_LISTING_TABLE)


# --- Helper functions extracted for clarity ---

def _get_meli_item_status(url, headers, meli_id):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get('status'), next(iter(data.get('sub_status') or []), 'good'), data.get('sold_quantity', 0)
    except Exception as e:
        logger.error(f"Error getting status for {meli_id}: {e}")
        return None, None, 0

def _update_family_name(url, headers, family_name):
    try:
        response = requests.put(f"{url}/family_name", json={"family_name": family_name}, headers=headers, timeout=10)
        if response.status_code < 300:
            logger.info("Family Name updated.")
        else:
            logger.error(f"Failed to update family name: {response.text}")
    except Exception as e:
        logger.error(f"Error updating family name: {e}")

def _update_listing_type(url, headers, listing_type_id):
    try:
        response = requests.post(f"{url}/listing_type", json={"id": listing_type_id}, headers=headers, timeout=10)
        if response.status_code < 300:
            logger.info("Listing Type updated.")
        else:
            # It's not critical, just log the error
            logger.warning(f"Could not update listing type: {response.text}")
    except Exception as e:
        logger.warning(f"Error updating listing type: {e}")

def _reactivate_item(url, headers, meli_id, product_listing_id):
    try:
        response = requests.put(url, json={"status": "active"}, headers=headers, timeout=10)
        if response.status_code < 300:
            logger.info(f"Item {meli_id} reactivated.")
        else:
            error = json.dumps([response.json()], ensure_ascii=False)
            _update_record(product_listing_id, {'status': 'Failed to Reactivate.', 'reason': error, 'remedy': 'None'}, PRODUCT_LISTING_TABLE)
    except Exception as e:
        logger.error(f"Error reactivating item: {e}")
 


def pause(payload):
    """Changes item status to paused in Mercado Libre"""

    product_id = payload.get('product_id')
    account_id = payload.get('account_id')
    token = get_access_token(account_id).get('access_token')

    logger.info("Running Pause Action on Mercadolibre")
    item_data = get_data_for_meli(product_id)
    meli_id = item_data['meli_id'] 
    product_listing_id = item_data['product_listing_id']

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
        data = {
        'status': 'Paused.', 
        'reason': 'User Action.', 
        'remedy': 'None', 
        }
        _update_record(product_listing_id, data, PRODUCT_LISTING_TABLE)

    else:
        error = json.dumps([response.json()], ensure_ascii=False)
        data = {
        'status': 'Failed to Pause.', 
        'reason': error, 
        'remedy': 'None', 
        }
        _update_record(product_listing_id, data, PRODUCT_LISTING_TABLE)
    return


def delete(payload):
    """"""

    product_id = payload.get('product_id')
    account_id = payload.get('account_id')
    token = get_access_token(account_id).get('access_token')

    logger.info("Running Delete Action on Mercadolibre")
    item_data = get_data_for_meli(product_id)
    meli_id = item_data['meli_id']
    product_listing_id = item_data['product_listing_id']

    if meli_id is None:
        logger.error(f"Product: {product_id} is not published, nothing to delete.")
        return
    
    url = f"https://api.mercadolibre.com/items/{meli_id}"
    headers = { "Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    var_closed = {"status": "closed"}
    var_deleted = {"deleted": "true"}
    requests.put(url=url, json=var_closed, headers=headers)
    requests.put(url=url, json=var_deleted, headers=headers)
    resp_delete = requests.put(url=url, json=var_deleted, headers=headers)

    # 200 = deleted now; 404 = already gone → both mean "nothing left to track"
    if resp_delete.status_code in (200, 404):
        _delete_record(product_listing_id, PRODUCT_LISTING_TABLE)
    else:
        error = json.dumps([resp_delete.json()])
        data = {'status': 'Failed to Delete.', 'reason': error, 'remedy': 'None'}
        _update_record(product_listing_id, data, PRODUCT_LISTING_TABLE)
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

