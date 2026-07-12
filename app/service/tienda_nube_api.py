from app.service.database import ( 
    get_method,
    upsert_method,
    update_method
)
from app.service.google_pictures import process_images_storage
from app.service.secrets import tienda_nube_secrets
import requests
import json
from datetime import datetime
from unidecode import unidecode
from app.utils.logger import logger
from app.settings.config import SCHEMA_INVENTORY,SCHEMA_MERCADOLIBRE,SCHEMA_TNUBE


PRODUCTS_TABLE='product_catalog_sync'
ATTRIBUTES_TABLE='attributes'
PRODUCT_STATUS_TABLE='product_status'
CATEGORIES_TABLE='categories'

def get_data_for_tnube(item_id):
    """"""
    query = {
        'q_columns': [
            'a.price',
            'a.product_name',
            'a.product_image_b_format_url',
            'a.stock',
            'a.cost',
            'a.product_name_meli',
            'a.description',
            'a.brand',
            'a.dimentions',
            'a.price_tienda_nube',
            'a.product_category',
            'b.id as attribute_id',
            'b.seo_title',
            'b.seo_description',
            'b.barcode',
            'b.video_url',
            'b.tags',
            'b.promotional_price',
            'b.mpn',
            'b.age_group',
            'b.gender',
            'c.product_id',
            'c.variant_id',
            'd.id as category_id', 
            'd.name as category_name',
            'e.settings'
        ],
        'q_from':f'FROM {SCHEMA_INVENTORY}.{PRODUCTS_TABLE} as a',
        'q_join': [
            f'LEFT JOIN {SCHEMA_TNUBE}.{ATTRIBUTES_TABLE} as b on b.item_id = a.id',
            f'LEFT JOIN {SCHEMA_TNUBE}.{PRODUCT_STATUS_TABLE} as c on b.id = c.attribute_id ',
            f'LEFT JOIN {SCHEMA_TNUBE}.{CATEGORIES_TABLE} as d on d.name = a.product_type_path',
            f'LEFT JOIN {SCHEMA_MERCADOLIBRE}.{ATTRIBUTES_TABLE} as e on e.item_id = a.id',],
        'q_where': f'WHERE a.id = {item_id}',
        'q_limit':'LIMIT 1'
    }
    item_data = get_method(query)
    return item_data


def get_category(category_name):
    """"""
    query = {
        'q_columns': ['a.name',],
        'q_from':  f'FROM {SCHEMA_TNUBE}.{CATEGORIES_TABLE} as a',
        'q_where': f"WHERE a.name = '{category_name}'",
        'q_limit':'LIMIT 1'
    }
    category_name = get_method(query)
    return category_name


def aux_base_products_url():
    token, user_id = tienda_nube_secrets()
    url_base = f"https://api.tiendanube.com/v1/{user_id}/products"
    headers = {
        "Authentication": f"bearer {token}",
        "Content-Type": "application/json"}
    return url_base, headers


def aux_format_data(item_id):

    def _aux_cast(value):
        if value is None:
            return 0
        else:
            return int(value)
        
    def _aux_dimentions(data):
        dimentions = data.get("dimentions", None)
        if dimentions:
            dimentions = dimentions.split("x")
            height = int(dimentions[0])
            width = int(dimentions[1])
            depth = int(dimentions[2].split(',')[0])
            weight = int(float(dimentions[2].split(',')[1])/1000)
            dimtions_norm = {
                "height":height,
                "width":width,
                "depth":depth,
                "weight":weight,
            }
            return dimtions_norm
        else:
            return {}
        
    data = get_data_for_tnube(item_id)

    dimtions_norm = _aux_dimentions(data)
    attribute_id = data.get("attribute_id")
    product_id = data.get("product_id", None)
    variant_id = data.get("variant_id", None)

    #public_images = process_images_storage(item_id)
    public_images=[]
    if public_images == []:
        logger.info("Public Images in Drive not founded, using image from Bitcram..")
        public_images = [{'src': data["product_image_b_format_url"]}]
    else:
        for i in public_images:
            i['src'] = i['source']
            i.pop('source')

    
    category_id = data["category_id"] or 39076803
    product_name = data["product_name_meli"] or data["product_name"]

    all_settings_groups = json.loads(data.get("settings"))
    for settings_group in all_settings_groups:
        for section_name in settings_group:
            if section_name == "shipping":
                for variable in settings_group[section_name]:
                    if variable.get('id') == 'FREE_SHIPPING':
                        free_shipping = variable.get('user_input_value')

    product_data = {
        "name": {"es": product_name},
        "description": {"es": data.get("description", None)},
        "seo_title": {"es": product_name},
        "seo_description": {"es": data.get("seo_description", None)},
        "free_shipping": True if free_shipping.lower() == 'true' else False,
        "brand": data.get("brand", None),
        "video_url": data.get("video_url", None),
        "images": public_images,
        "tags": data.get("tags", None),
        "categories": [category_id]
    }
    
    variant_data = [
        {
        "price": _aux_cast(data.get("price_tienda_nube", 0)),
        "promotional_price": _aux_cast(data.get("promotional_price", 0)),
        "stock": _aux_cast(data.get("stock", 0)),
        "sku": data.get("sku", None),
        "barcode": data.get("barcode", None),
        "weight": dimtions_norm.get("weight", 0),
        "width": dimtions_norm.get("width", 0),
        "height": dimtions_norm.get("height", 0),
        "depth": dimtions_norm.get("depth", 0),
        "cost": _aux_cast(data.get("cost", 0)),
        "mpn": data.get("mpn", None),
        "age_group": data.get("age_group", None),
        "gender": data.get("gender", None),
        }
    ]

    return product_data, variant_data, attribute_id, product_id, variant_id

##==========================PUBLISH=================================##

def tienda_nube_publish_item(item_id):
    
    logger.info("publish process started")
    product_data, variant_data, attribute_id, product_id, variant_id = aux_format_data(item_id)
    if product_id:
        logger.info("product already published, nothing to do.")
    else:
        db_data = {
            'attribute_id':{'value':None, 'type':'signed'},
            'product_id':{'value':None, 'type':'signed'},
            'variant_id':{'value':None, 'type':'signed'},
            'response':{'value':None, 'type':'char'},
            'updated_at':{'value':None, 'type':'datetime'},
        }
        url_base, headers = aux_base_products_url()
        product_data['variants'] = variant_data
        response = requests.post(url_base, headers=headers, data=json.dumps(product_data))
        if response.status_code == 201:
            logger.info("product correctly published!")
            db_data['attribute_id']['value'] = attribute_id
            db_data['product_id']['value'] = response.json()['id']
            db_data['variant_id']['value'] = response.json()['variants'][0]['id']
            db_data['response']['value'] = 'producto correctamente publicado'
            db_data['updated_at']['value'] = datetime.now()
            update_method(db_data, SCHEMA_TNUBE, PRODUCT_STATUS_TABLE)
        else:
            logger.info("product failed to be published!!")
            db_data['attribute_id']['value'] = attribute_id
            db_data['response']['value'] = f"Failed to publish: {json.dumps(response.json(), ensure_ascii=False)}"
            db_data['updated_at']['value'] = datetime.now()
            update_method(db_data, SCHEMA_TNUBE, PRODUCT_STATUS_TABLE)
    return


##==========================UPDATE=================================##

def tienda_nube_update_item(item_id):
    
    logger.info("update process started")
    url_base, headers = aux_base_products_url()
    product_data, variant_data, attribute_id, product_id, variant_id = aux_format_data(item_id)
    db_data = {
            'attribute_id':{'value':attribute_id, 'type':'signed'},
            'response':{'value':None, 'type':'char'},
            'updated_at':{'value':None, 'type':'datetime'},
        }

    images = product_data.pop('images')
    url_upd_product = f"{url_base}/{product_id}"
    url_upd_variant = f"{url_upd_product}/variants/{variant_id}"
    url_upd_image = f"{url_upd_product}/images"

    response = requests.put(url_upd_product, headers=headers, data=json.dumps(product_data))
    logger.info("Step 1: Upadting Product (general)")
    if response.status_code == 200:
        logger.info("Step 1: Done")
    else:
        logger.error("product failed to update")
        db_data['response']['value'] = f"Failed to update: {json.dumps(response.json(), ensure_ascii=False)}"
        db_data['updated_at']['value'] = datetime.now()
        update_method(db_data, SCHEMA_TNUBE, PRODUCT_STATUS_TABLE)
        return

    logger.info("Step 2: Upadting Product (variant)")
    response = requests.put(url_upd_variant, headers=headers, data=json.dumps(variant_data[0]))
    if response.status_code == 200:
        logger.info("Step 2: Done")
    else:
        logger.error("variant failed to update")
        db_data['response']['value'] = f"Failed to update: {json.dumps(response.json(), ensure_ascii=False)}"
        db_data['updated_at']['value'] = datetime.now()
        update_method(db_data, SCHEMA_TNUBE, PRODUCT_STATUS_TABLE)
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

    logger.info("Step 3: Done")
    db_data['response']['value'] = 'producto correctamente actualizado'
    db_data['updated_at']['value'] = datetime.now()
    update_method(db_data, SCHEMA_TNUBE, PRODUCT_STATUS_TABLE)


###==========================DELETE=================================##
def tienda_nube_delete_item(item_id):
    logger.info("delete process started")
    db_data = {
        'attribute_id':{'value':None, 'type':'signed'},
        'response':{'value':None, 'type':'char'},
        'updated_at':{'value':None, 'type':'datetime'},
    }
    url_base, headers = aux_base_products_url()
    product_data, variant_data, attribute_id, product_id, variant_id = aux_format_data(item_id)
    del_url = f"{url_base}/{product_id}"
    response = requests.delete(del_url, headers=headers)
    if response.status_code == 200:
        logger.info("product correctly deleted!")
        db_data['attribute_id']['value'] = attribute_id
        db_data['product_id'] = {'value': None, 'type':'signed'}
        db_data['variant_id'] = {'value': None, 'type':'signed'}
        db_data['response']['value'] = 'producto correctamente eliminado'
        db_data['updated_at']['value'] = datetime.now()
        update_method(db_data, SCHEMA_TNUBE, PRODUCT_STATUS_TABLE)
    else:
        logger.info("product failed to delete")
        db_data['attribute_id']['value'] = attribute_id
        db_data['response']['value'] = f"Failed to delete: {json.dumps(response.json(), ensure_ascii=False)}"
        db_data['updated_at']['value'] = datetime.now()
        update_method(db_data, SCHEMA_TNUBE, PRODUCT_STATUS_TABLE)
    return


def create_categories(category_name):

    logger.info("Creating Category process started")
    if get_category(category_name):
        logger.info(f"Category {category_name} already exists, nothing to do.")
        return
    else:
        token, user_id = tienda_nube_secrets()
        url = f"https://api.tiendanube.com/v1/{user_id}/categories"
        headers = {
            "Authentication": f"bearer {token}",
            "Content-Type": "application/json"}

        payload = {
        "name": {
          "es": category_name}}

        response = requests.post(url=url,headers=headers,data=json.dumps(payload))
        if response.status_code < 300:
            logger.info(f"Category {category_name} succesfully created")
            response_dict = response.json()
            catgory_id = response_dict.get('id')
            response_dict.pop('id')
            catgory_name = response_dict.get('name').get('es')
            catgory_info = response_dict

            db_data = {
                'id':{'value':catgory_id, 'type':'signed'},
                'name':{'value':catgory_name, 'type':'char'},
                'data':{'value':unidecode(json.dumps(catgory_info, ensure_ascii=False).replace("'","").replace("\\n","")), 'type':'json'},
            }
            upsert_method(db_data, SCHEMA_TNUBE, CATEGORIES_TABLE)
        else:
            logger.error(f'Error creating category {category_name} : {response.json()}')

            