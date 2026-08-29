import json
import uuid
from unidecode import unidecode
import requests
from app.utils.logger import logger
from app.service.secrets import meli_secrets
#from app.integrations.mercadolibre.meli_api import publish_item
from app.db.database import get_method, upsert_method
from app.settings.config import SCHEMA_MERCADOLIBRE, SCHEMA_INVENTORY

PRODUCTS_TABLE = 'product_catalog_sync'
ATTRIBUTES_TABLE = 'attributes'
GRID_TABLE = 'size_grid'
SITE_ID = "MLA"

def get_headers():
    token = meli_secrets()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }


def get_row_id(size_grid_id, size):
    grid = requests.get(
        f"https://api.mercadolibre.com/catalog/charts/{size_grid_id}",
        headers=get_headers()
    ).json()

    for row in grid.get("rows", []):
        for attr in row.get("attributes", []):
            if attr.get("id") == "SIZE":
                if attr.get("values", [{}])[0].get("name") == size:
                    return row.get("id")

    logger(f"Size '{size}' not found in grid {size_grid_id}")
    return None


def get_data_from_attributes(item_id):
    """"""
    logger.info(f"Getting data from: {ATTRIBUTES_TABLE} and {PRODUCTS_TABLE}")
    query = {
        'q_columns': [
            'a.id',
            'a.item_id',
            'a.category_id',
            'a.category_options',
            'a.settings',
            'b.brand'
        ],
        'q_from':f'FROM {SCHEMA_MERCADOLIBRE}.{ATTRIBUTES_TABLE} as a',
        'q_join':[f'LEFT JOIN {SCHEMA_INVENTORY}.{PRODUCTS_TABLE} as b on a.item_id = b.id'],
        'q_where': f'WHERE a.item_id = {item_id}',
        'q_limit':'LIMIT 1'
    }
    item_data = get_method(query)
    return item_data[0]


def get_data_from_size_grid(item_id):
    """"""
    logger.info(f"Getting data from: {GRID_TABLE}")
    query = {
        'q_columns': [
            'a.id',
            'a.settings'
        ],
        'q_from':f'FROM {SCHEMA_MERCADOLIBRE}.{GRID_TABLE} as a',
        'q_where': f'WHERE a.item_id = {item_id}',
        'q_limit':'LIMIT 1'
    }
    item_data = get_method(query)
    return item_data[0]


def get_base_data(item_id):
    """"""
    logger.info("Creating base data.")
    base_info = get_data_from_attributes(item_id)
    att_id = base_info['id']
    category_id = base_info['category_id']
    brand = base_info['brand']
    category_options = json.loads(base_info['category_options'])
    settings = json.loads(base_info['settings'])
    for i in category_options:
        if i['category_id'] == category_id:
            domain_id = i['domain_id']
    for section in settings:
        for items in section.values():
            for item in items:
                if item["id"] == "GENDER":
                    gender = item["user_input_value"]
                elif item["id"] == "SIZE":
                    size = item["user_input_value"]

    return brand, domain_id, gender, settings, att_id, size



def request_tech_spec(BRAND, DOMAIN_ID, GENDER):
    """"""
    logger.info("Requesting technical specs")
    response = requests.get(f"https://api.mercadolibre.com/domains/{DOMAIN_ID}/technical_specs",
                headers=get_headers())
    response.raise_for_status()
    data = response.json()

    default_brand = {"id": None,"name": BRAND}
    default_gender = {"id": None,"name": GENDER}
    required=[]
    for group in data["input"]["groups"]:
        for component in group.get("components", []):
            for attr in component.get("attributes", []):
                if attr.get("id") == "BRAND":
                    for value in attr.get("values", []):
                        if value.get("name", "").lower() == BRAND.lower():
                            default_brand = {"id": value["id"],"name": value["name"]}
                            break
                elif attr.get("id") == "GENDER":
                    for value in attr.get("values", []):
                        if value.get("name", "").lower() == GENDER.lower():
                            default_gender = {"id": value["id"],"name": value["name"]}
                            break
                elif "grid_template_required" in attr.get("tags", []):
                    required.append(attr)
            for subcomponent in component.get("components", []):
                for attr in subcomponent.get("attributes", []):
                    if "grid_template_required" in attr.get("tags", []):
                        required.append(attr)
    required.append({"id": 'BRAND',"name": 'Marca',"values": default_brand})
    required.append({"id": 'GENDER',"name": 'Género',"values": default_gender})
    return required


def create_template(item_id):
    """"""
    BRAND, DOMAIN_ID, GENDER, *_  = get_base_data(item_id)
    required = request_tech_spec(BRAND, DOMAIN_ID, GENDER)

    logger.info("Creating Template.")
    URL = f"https://api.mercadolibre.com/domains/{DOMAIN_ID}/technical_specs?section=grids"

    attributes = [
        {
            "id": attr["id"],
            "name": attr["name"],
            "value_id": attr["values"]["id"],
            "value_name": attr["values"]["name"],
            "value_struct": None,
            "values": [
                {
                    "id": attr["values"]["id"],
                    "name": attr["values"]["name"],
                    "struct": None
                }
            ],
            "attribute_group_id": "OTHERS",
            "attribute_group_name": "Otros"
        }
        for attr in required
    ]

    response = requests.post(URL, headers=get_headers(), json={"attributes": attributes})
    response_data = response.json()

    MEASURE_TYPES = {"BODY_MEASURE", "CLOTHING_MEASURE", "MIXED_MEASURE"}

    required_template = []
    measure_type = None

    required_template.append({
        "id": 'GRID_NAME',
        "name": 'Nombre del template de Talla',
        "user_input": None
    })

    for i in required:
        if i["id"] == "BRAND":
            required_template.append(i)

    for group in response_data["input"]["groups"]:
        for component in group.get("components", []):
            for subcomponent in component.get("components", []):
                for attr in subcomponent.get("attributes", []):
                    tags = set(attr.get("tags", []))

                    if "required" not in tags or attr.get("id") in {"BRAND", "SIZE"}:
                        continue

                    measure = tags & MEASURE_TYPES

                    if measure:
                        if measure_type is None:
                            measure_type = next(iter(measure))
                        elif measure_type not in measure:
                            continue

                    required_template.append({
                        **{
                            k: v for k, v in attr.items()
                            if k not in {"tags", "hierarchy", "relevance"}
                        },
                        **({"user_input": [{}]} if attr["id"] not in {"GENDER", "FILTRABLE_SIZE"} else {})
                    })

    clean_json = unidecode(json.dumps(required_template, ensure_ascii=False).replace("'","").replace("\\n",""))
    data = {
        'id': {'value': str(uuid.uuid4()), 'type': 'CHAR'},
        'item_id': {'value': 188133, 'type': 'SIGNED'},
        'size_grid_id': {'value': None, 'type': 'SIGNED'},
        'settings': {'value': clean_json, 'type': 'JSON'},
        'response': {'value': None, 'type': 'CHAR'},
    }
    upsert_method(data, SCHEMA_MERCADOLIBRE, 'size_grid')


def create_grid(item_id):
    """"""
    logger.info("Creating Grid.")
    BRAND, DOMAIN_ID, GENDER, SETTINGS, ATT_ID, SIZE = get_base_data(item_id)

    data = get_data_from_size_grid(item_id)
    attributes = json.loads(data['settings'])
    size_grid_id = data['id']

    rows_by_size = {}

    for attr in attributes:
            attr_id = attr["id"]

            if attr_id == 'GRID_NAME':
                GRID_NAME = attr['user_input']
                continue
            if attr_id == "FILTRABLE_SIZE":
                FILTRABLE_SIZE_IDS = {v["name"]: v["id"] for v in attr.get("values", [])}
                continue
            if attr_id == "GENDER":
                GENDER = attr.get("values", [])[0]
                continue
            if attr_id == "BRAND":
                BRAND = attr.get("values")
                continue
            for item in attr.get("user_input", []):
                if not item:
                    continue
                size = item["SIZE"]
                rows_by_size.setdefault(size, {"SIZE": size})
                rows_by_size[size][attr_id] = item["value"]

    rows = []

    for row in rows_by_size.values():
        attributes = [
            {"id": "SIZE", "values": [{"name": row["SIZE"]}]},
            {
                "id": "FILTRABLE_SIZE",
                "values": [{
                    "id": FILTRABLE_SIZE_IDS[row["SIZE"]],
                    "name": row["SIZE"]
                }]
            }
        ]

        attributes += [
            {"id": attr_id, "values": [{"name": value}]}
            for attr_id, value in row.items()
            if attr_id not in ["SIZE", "FILTRABLE_SIZE"]
        ]

        rows.append({"attributes": attributes})


    body = {
        "names": {SITE_ID: GRID_NAME},
        "domain_id": DOMAIN_ID.split('-')[-1],
        "site_id": SITE_ID,
        "main_attribute": {
            "attributes": [{"site_id": SITE_ID, "id": "SIZE"}]
        },
        "attributes": [
            {"id": "GENDER", "values": [GENDER]},
            {"id": "BRAND", "values": [BRAND]}
        ],
        "rows": rows
    }


    response = requests.post(
        "https://api.mercadolibre.com/catalog/charts",
        headers=get_headers(),
        json=body
    )
    try:
        response.raise_for_status()
        size_grid_id = response.json()['id']
        data = {
            'id': {'value': size_grid_id, 'type': 'CHAR'},
            'item_id': {'value': item_id, 'type': 'SIGNED'},
            'size_grid_id': {'value': size_grid_id, 'type': 'SIGNED'},
            'response': {'value': 'success', 'type': 'CHAR'},
        }


        row_id = get_row_id(size_grid_id, SIZE)

        for section in SETTINGS:
            for items in section.values():
                for item in items:
                    if item["id"] == "SIZE_GRID_ID":
                        item["user_input_value"] = size_grid_id
                    if item["id"] == "SIZE_GRID_ROW_ID":
                        item["user_input_value"] = row_id
                        
        clean_json = unidecode(json.dumps(SETTINGS, ensure_ascii=False).replace("'","").replace("\\n",""))
        new_settings = {
            'id': {'value': ATT_ID, 'type': 'CHAR'},
            'settings': {'value': clean_json, 'type': 'JSON'},
        }
        upsert_method(new_settings, SCHEMA_MERCADOLIBRE, ATTRIBUTES_TABLE)
        #publish_item(item_id, meli_secrets())
  
    except requests.HTTPError:
        clean_json = unidecode(json.dumps(response.json(), 
                                          ensure_ascii=False).replace("'","").replace("\\n",""))
        data = {
            'id': {'value': size_grid_id, 'type': 'CHAR'},
            'item_id': {'value': item_id, 'type': 'SIGNED'},
            'response': {'value': clean_json, 'type': 'CHAR'},
        }
    upsert_method(data, SCHEMA_MERCADOLIBRE, GRID_TABLE)
