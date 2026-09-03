import requests
import json
from app.utils.logger import logger
from app.db.helpers import get_one, execute, get_all
from app.settings.config import SCHEMA_INVENTORY, SCHEMA_TIENDANUBE, SCHEMA_ACCOUNTS
import hashlib
from sqlalchemy import text
from app.db.engine import engine

LOCK_TIMEOUT = 30

PRODUCT_LISTING_TABLE= 'product_listings'
ATTRIBUTES_TABLE='attributes'
PRODUCTS_TABLE='products'
CATEGORIES_TABLE='categories'
CREDS_TABLE= 'credentials'
ACCOUNTS_TABLE= 'accounts'
IMAGES_TABLE= 'product_images'


def get_data_for_tnube(product_id):
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
        + "b.id AS product_listing_id, "
        + "b.tnube_id, "
        + "b.variant_id, "
        + "b.price AS price_tnube, "
        + "c.settings, "
        + "d.external_category_id "
        + "FROM " + SCHEMA_INVENTORY + "." + PRODUCTS_TABLE + " AS a "
        + "LEFT JOIN " + SCHEMA_TIENDANUBE + "." + PRODUCT_LISTING_TABLE + " AS b ON b.product_id = a.id "
        + "LEFT JOIN " + SCHEMA_TIENDANUBE + "." + ATTRIBUTES_TABLE + " AS c ON c.product_listing_id = b.id "
        + "LEFT JOIN " + SCHEMA_TIENDANUBE + "." + CATEGORIES_TABLE + " AS d ON d.id = c.category_id "
        + "WHERE a.id = :product_id "
    )
    row = get_one(sql, {"product_id": product_id,})
    return row


def get_nube_creds(account_id):
    sql = (
        "SELECT "
        + "a.external_account_id as user_id,"
        + "b.access_token "
        + "FROM " + SCHEMA_ACCOUNTS + "." + ACCOUNTS_TABLE + " AS a "
        + "JOIN " + SCHEMA_ACCOUNTS + "." + CREDS_TABLE + " AS b ON a.id = b.account_id "
        + "WHERE a.id = :account_id "
    )
    try:
        return get_one(sql, {"account_id": account_id,})
    except LookupError:
        return {}

def get_category(product_id):
    sql = (
        "SELECT "
        + "a.id, "
        + "a.category as official_category, "
        + "b.id  as product_listing_id, "
        + "c.id  as attrb_id, "
        + "d.id as category_id, "
        + "d.name as tiendanube_category "
        + "FROM " + SCHEMA_INVENTORY + "." + PRODUCTS_TABLE + " AS a "
        + "LEFT JOIN " + SCHEMA_TIENDANUBE + "." + PRODUCT_LISTING_TABLE + " AS b ON b.product_id = a.id "
        + "LEFT JOIN " + SCHEMA_TIENDANUBE + "." + ATTRIBUTES_TABLE + " AS c ON c.product_listing_id = b.id "
        + "LEFT JOIN " + SCHEMA_TIENDANUBE + "." + CATEGORIES_TABLE + " AS d ON TRIM(UPPER(d.name)) = TRIM(UPPER(a.category)) AND d.account_id = b.account_id "
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



def _insert_record(data, table):
    fields = []
    values = []
    params = {}

    for field, value in data.items():
        if value is not None:
            fields.append(field)
            values.append(f":{field}")
            params[field] = value

    if not fields:
        return None

    sql = (
        "INSERT INTO " + SCHEMA_TIENDANUBE + "." + table
        + " (" + ", ".join(fields) + ") "
        + "VALUES (" + ", ".join(values) + ")"
    )

    rowcount = execute(sql, params)
    logger.info("Rows Affected: %s", rowcount)
    
    # Since execute returns int, we need to query back the ID
    # Assuming the table has an 'id' column
    result = get_one(
        f"SELECT LAST_INSERT_ID() as id"
    )
    last_id = result['id'] if result else None
    
    logger.info("Inserted ID: %s", last_id)
    return last_id



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
        "UPDATE " + SCHEMA_TIENDANUBE + "." + table
        + " SET " + ", ".join(fields)
        + " WHERE id = :id"
    )
    rowcount = execute(sql, params)
    logger.info("Rows Affected: ")
    logger.info(rowcount)



def _delete_record(id, table):
    logger.info(f"Deleting: {id}")
    sql = (
        "DELETE FROM " + SCHEMA_TIENDANUBE + "." + table
        + " WHERE id = :id"
    )
    rowcount = execute(sql, {'id': id})
    logger.info("Rows Affected: ")
    logger.info(rowcount)



def aux_format_data(product_id):


    def _aux_dimensions(data):
        dimensions = data.get("dimensions", None)
        if dimensions:
            dimensions = dimensions.split("x")
            height = int(dimensions[0])
            width = int(dimensions[1])
            depth = int(dimensions[2].split(',')[0])
            weight = int(float(dimensions[2].split(',')[1])/1000)
            dimtions_norm = {
                "height":height,
                "width":width,
                "depth":depth,
                "weight":weight,
            }
            return dimtions_norm
        else:
            return {}
        
    

    data = get_data_for_tnube(product_id)

    #public_images = process_images_storage(item_id) ###probar primero con mercaodlibre workflow.
    public_images=[]
    if public_images == []:
        logger.info("Without images in Folder, using images from DB.")
        product_id = data['id']
        public_images = get_product_images(product_id)
        public_images = [{'src': image["url"]} for image in public_images[:5]

    else:
        for i in public_images:
            i['src'] = i['source']
            i.pop('source')

    product_listing_id =  data.get('product_listing_id')
    dimensions = _aux_dimensions(data)
    tnube_id = data.get("tnube_id")
    variant_id = data.get("variant_id")
    category_id = data["external_category_id"] or 39076803 #generic gategory.
    product_name = data["name_edited"] or data["name"]
    price = int(data["price_tnube"] or data["price"] or 0)
    cost = int(data["cost"] or 0)
    stock = data["stock"]
    sku = data["sku"]


    settings = json.loads(data.get("settings") or "{}")

    
    seo_title = (
        settings.get("SEO_TITLE", {}).get("USER_INPUT_VALUE")
        or settings.get("SEO_TITLE", {}).get("DEFAULT_VALUE")
    )
    seo_description = (
        settings.get("SEO_DESCRIPTION", {}).get("USER_INPUT_VALUE")
        or settings.get("SEO_DESCRIPTION", {}).get("DEFAULT_VALUE")
    )
    barcode = (
        settings.get("BARCODE", {}).get("USER_INPUT_VALUE")
        or settings.get("BARCODE", {}).get("DEFAULT_VALUE")
    ) 
    video_url = (
        settings.get("VIDEO_URL", {}).get("USER_INPUT_VALUE")
        or settings.get("VIDEO_URL", {}).get("DEFAULT_VALUE")
    )
    tags = (
        settings.get("TAGS", {}).get("USER_INPUT_VALUE")
        or settings.get("TAGS", {}).get("DEFAULT_VALUE")
    )
    promotional_price = (
        settings.get("PROMOTIONAL_PRICE", {}).get("USER_INPUT_VALUE")
        or settings.get("PROMOTIONAL_PRICE", {}).get("DEFAULT_VALUE")
    )
    mpn = (
        settings.get("MPN", {}).get("USER_INPUT_VALUE")
        or settings.get("MPN", {}).get("DEFAULT_VALUE")
    )
    age_group = (
        settings.get("AGE_GROUP", {}).get("USER_INPUT_VALUE")
        or settings.get("AGE_GROUP", {}).get("DEFAULT_VALUE")
    )
    gender = (
        settings.get("GENDER", {}).get("USER_INPUT_VALUE")
        or settings.get("GENDER", {}).get("DEFAULT_VALUE")
    ) 
    free_shipping = (
        settings.get("FREE_SHIPPING", {}).get("USER_INPUT_VALUE")
        or settings.get("FREE_SHIPPING", {}).get("DEFAULT_VALUE")
    )

    product_data = {
        "name": {"es": product_name},
        "description": {"es": data.get("description")},
        "seo_title": {"es": seo_title},
        "seo_description": {"es": seo_description},
        "free_shipping": free_shipping,
        "brand": data.get("brand"),
        "video_url": video_url,
        "images": public_images,
        "tags": tags,
        "categories": [category_id]
    }
    
    variant_data = [
        {
        "price": price,
        "promotional_price": promotional_price,
        "stock": stock,
        "sku": sku,
        "barcode": barcode,
        "weight": dimensions.get("weight", 0),
        "width": dimensions.get("width", 0),
        "height": dimensions.get("height", 0),
        "depth": dimensions.get("depth", 0),
        "cost": cost,
        "mpn": mpn,
        "age_group": age_group,
        "gender": gender,
        }
    ]

    result = {
        'product_listing_id' : product_listing_id,
        'product_data': product_data, 
        'variant_data': variant_data, 
        'tnube_id': tnube_id, 
        'variant_id': variant_id
    }
    return result 




##==========================PUBLISH=================================##




def publish(payload):
    
    logger.info("publish process started")
    product_id = payload['product_id']

    result = aux_format_data(product_id)
    product_listing_id =  result.get('product_listing_id')
    product_data =  result.get('product_data')
    variant_data =  result.get('variant_data')
    tnube_id =  result.get('tnube_id')

    if tnube_id:
        logger.info("product already published, nothing to do.")
        return

    else:
        account_id = payload['account_id']
        creds = get_nube_creds(account_id)
        token = creds.get('access_token')
        user_id = creds.get('user_id')

        url_base = f"https://api.tiendanube.com/v1/{user_id}/products"
        headers = { "Authentication": f"bearer {token}", "Content-Type": "application/json"}

        product_data['variants'] = variant_data
        response = requests.post(url_base, headers=headers, data=json.dumps(product_data, default=str))

        if response.status_code == 201:
            tnube_id = response.json()['id']
            response = requests.get(url_base + "/" + str(tnube_id), headers=headers)
            product = response.json()
            data = {
                'tnube_id': response.json()['id'], 
                'variant_id':response.json()['variants'][0]['id'],
                'permalink': product["canonical_url"], 
                'status': 'Published', 
                'reason': 'None', 
                'remedy': 'None', 
            }
            _update_record(product_listing_id, data, PRODUCT_LISTING_TABLE)

        else:
            logger.error("product failed to be published!")
            error = json.dumps([response.json()], ensure_ascii=False)
            data = {
            'status': 'Failed to Publish.', 
            'reason': error, 
            'remedy': 'None', 
            }
            _update_record(product_listing_id, data, PRODUCT_LISTING_TABLE)

    return



##==========================UPDATE=================================##

def update(payload):
    
    logger.info("update process started")
    product_id = payload['product_id']

    result = aux_format_data(product_id)
    product_listing_id =  result.get('product_listing_id')
    product_data =  result.get('product_data')
    variant_data =  result.get('variant_data')
    tnube_id =  result.get('tnube_id')
    variant_id =  result.get('variant_id')


    if tnube_id is None:
        logger.info("product is not published, nothing to do.")
        return


    account_id = payload['account_id']
    creds = get_nube_creds(account_id)
    token = creds.get('access_token')
    user_id = creds.get('user_id')

    url_base = f"https://api.tiendanube.com/v1/{user_id}/products"
    headers = { "Authentication": f"bearer {token}", "Content-Type": "application/json"}


    images = product_data.pop('images')
    url_upd_product = f"{url_base}/{tnube_id}"
    url_upd_variant = f"{url_upd_product}/variants/{variant_id}"
    url_upd_image = f"{url_upd_product}/images"

    response = requests.put(url_upd_product, headers=headers, data=json.dumps(product_data))
    logger.info("Step 1: Upadting Product (general)")
    if response.status_code == 200:
        logger.info("Step 1: Done")
    else:
        logger.error("product failed to be updated!")
        error = json.dumps([response.json()], ensure_ascii=False)
        data = {
        'status': 'Failed to Update.', 
        'reason': error, 
        'remedy': 'None', 
        }
        _update_record(product_listing_id, data, PRODUCT_LISTING_TABLE)


        return

    logger.info("Step 2: Upadting Product (variant)")
    response = requests.put(url_upd_variant, headers=headers, data=json.dumps(variant_data[0]))
    if response.status_code == 200:
        logger.info("Step 2: Done")
    else:
        logger.error("variant failed to be updated!")
        error = json.dumps([response.json()], ensure_ascii=False)
        data = {
        'status': 'Failed to Update.', 
        'reason': error, 
        'remedy': 'None', 
        }
        _update_record(product_listing_id, data, PRODUCT_LISTING_TABLE)
        return

    logger.info("Step 3: Upadting Product (images)")
    response = requests.get(url_upd_image, headers=headers)
    product_images = response.json()
    for p_image in product_images:
        id = p_image['id']
        response = requests.delete(f"{url_upd_image}/{id}", headers=headers)
        if response.status_code == 200:
            logger.info("image deleted correctly")
        else:
            logger.info(f"error deleting image {id}")

    for image in images:
        response = requests.post(url_upd_image, headers=headers, data=json.dumps(image))
        if response.status_code == 201:
            logger.info("image correctly loaded")
            continue
        else:
            logger.error("images failed to update")
            logger.info(str(response.json()))
            continue


    logger.info("Product correctly updated")
    data = {'status': 'Updated.', 'reason': 'None', 'remedy': 'None'}
    _update_record(product_listing_id, data, PRODUCT_LISTING_TABLE)
    return



###==========================DELETE=================================##
def delete(payload):

    logger.info("delete process started")

    product_id = payload['product_id']

    result = aux_format_data(product_id)
    product_listing_id =  result.get('product_listing_id')
    tnube_id =  result.get('tnube_id')

    if tnube_id is None:
        logger.info("product is not published, nothing to do.")
        return

    account_id = payload['account_id']
    creds = get_nube_creds(account_id)
    token = creds.get('access_token')
    user_id = creds.get('user_id')

    url_base = f"https://api.tiendanube.com/v1/{user_id}/products"
    headers = { "Authentication": f"bearer {token}", "Content-Type": "application/json"}

    del_url = f"{url_base}/{tnube_id}"
    response = requests.delete(del_url, headers=headers)
    if response.status_code == 200:
        logger.info("product correctly deleted!")
        _delete_record(product_listing_id, PRODUCT_LISTING_TABLE)

    else:
        logger.info("product failed to delete")
        error = json.dumps([response.json()], ensure_ascii=False)
        data = {
        'status': 'Failed to Delete.', 
        'reason': error, 
        'remedy': 'None', 
        }
        _update_record(product_listing_id, data, PRODUCT_LISTING_TABLE)
    return




def create_categories(payload):

    logger.info("Creating Category process started")

    product_id = payload['product_id']
    account_id = payload['account_id']
    category_info = get_category(product_id)
    attrb_id = category_info.get('attrb_id')
    category_name = category_info.get('official_category')

    # One lock per account+category: two tenants with the same category name never block each other.
    lock_name = "tnube-category-" + str(account_id) + "-" + hashlib.md5(
        category_name.strip().upper().encode()).hexdigest()

    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        acquired = conn.execute(
            text("SELECT GET_LOCK(:name, :timeout)"),
            {"name": lock_name, "timeout": LOCK_TIMEOUT}).scalar()
        if acquired != 1:
            raise Exception("Could not acquire category lock: " + str(category_name))

        # RE-CHECK inside the lock: whoever waited on the lock will now
        # find the category already created and just link it.
        category_info = get_category(product_id)
        if category_info.get('tiendanube_category'):
            logger.info(f"Category: {category_info.get('tiendanube_category')} already exists.")
            data = {'category_id': category_info.get('category_id')}
            _update_record(attrb_id, data, ATTRIBUTES_TABLE)
            return

        creds = get_nube_creds(account_id)
        token = creds.get('access_token')
        user_id = creds.get('user_id')
        url = f"https://api.tiendanube.com/v1/{user_id}/categories"
        headers = {
                "Authentication": f"bearer {token}",
                "Content-Type": "application/json"}
        
        payload = {
        "name": {
          "es": category_name}}
    
        response = requests.post(url=url,headers=headers,data=json.dumps(payload))
        if response.status_code < 300:
            logger.info(f"Category: {category_name} succesfully created")
            response_dict = response.json()
            category_id = response_dict.get('id')
            response_dict.pop('id')
            catgory_info = response_dict
    
            data = {
            'account_id': account_id, 
            'external_category_id': category_id, 
            'name': category_name, 
            'data': json.dumps(catgory_info), 
            }
            last_id = _insert_record(data, CATEGORIES_TABLE)
    
            data = {'category_id': last_id}
            _update_record(attrb_id, data, ATTRIBUTES_TABLE)
        else:
            logger.error(f'Error creating category {category_name} : {response.json()}')

    finally:
        conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": lock_name})
        conn.close()