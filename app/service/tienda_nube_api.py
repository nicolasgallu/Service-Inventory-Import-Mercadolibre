from app.service.database import get_tienda_nube_item_data,load_tienda_nube_product_status,delete_tienda_nube_product_status
from app.service.secrets import tienda_nube_secrets
import requests
import json
from datetime import datetime

def aux_base_url():
    token, user_id = tienda_nube_secrets()
    url_base = f"https://api.tiendanube.com/v1/{user_id}/products"
    headers = {
        "Authentication": f"bearer {token}",
        "Content-Type": "application/json"}
    return url_base, headers

def aux_format_data(item_id, public_images):

    def _aux_cast(value):
        if value is None:
            return 0
        else:
            return int(value)

    data = get_tienda_nube_item_data(item_id)
    attribute_id = data.get("attribute_id")
    product_id = data.get("product_id", None)
    variant_id = data.get("variant_id", None)

    product_data = {
        "name": {"es": data.get("product_name_meli", None)},
        "description": {"es": data.get("description", None)},
        "seo_title": {"es": data.get("seo_title", None)},
        "seo_description": {"es": data.get("seo_description", None)},
        "free_shipping": False if data.get("free_shipping", False) == 0 else True,
        "brand": data.get("brand", None),
        "video_url": data.get("video_url", None),
        "images": public_images,
        "tags": data.get("tags", None)
    }

    variant_data = [
        {
        "price": _aux_cast(data.get("price_tienda_nube", 0)),
        "promotional_price": _aux_cast(data.get("promotional_price", 0)),
        "stock": _aux_cast(data.get("stock", 0)),
        "sku": data.get("sku", None),
        "barcode": data.get("barcode", None),
        "weight": _aux_cast(data.get("weight", 0)),
        "width": _aux_cast(data.get("width", 0)),
        "height": _aux_cast(data.get("height", 0)),
        "depth": _aux_cast(data.get("depth", 0)),
        "cost": _aux_cast(data.get("cost", 0)),
        "mpn": data.get("mpn", None),
        "age_group": data.get("age_group", None),
        "gender": data.get("gender", None),
        }
    ]

    return product_data, variant_data, attribute_id, product_id, variant_id

##==========================PUBLISH=================================##

def tienda_nube_publish_item(item_id, public_images):

    product_data, variant_data, attribute_id, product_id, variant_id = aux_format_data(item_id, public_images)

    if product_id:
        print("product already published, nothing to do.")
        return None
    
    else:
        url_base, headers = aux_base_url()
        product_data['variant'] = variant_data
        response = requests.post(url_base, headers=headers, data=json.dumps(product_data))
        if response.status_code == 201:
            print("product correctly published!")
            product_id = response.json()['id']
            variant_id = response.json()['variants'][0]['id']
            data = {
                "attribute_id": attribute_id,
                "product_id": product_id, 
                "variant_id": variant_id,
                "response": "producto correctamente publicado",
                "updated_at": datetime.now()}
            load_tienda_nube_product_status(data)
            return product_id, variant_id    
        else:
            print("product failed to be published!")
            data = {
                "attribute_id": attribute_id,
                "product_id": None, 
                "variant_id": None,
                "response": f"fallo en la publicacion del item: {response.json()}",
                "updated_at": datetime.now()}
            load_tienda_nube_product_status(data)


##==========================UPDATE=================================##

def tienda_nube_update_item(item_id, public_images):
    
    print("updating process started")
    url_base, headers = aux_base_url()
    product_data, variant_data, attribute_id, product_id, variant_id = aux_format_data(item_id, public_images)

    images = product_data.pop('images')
    url_upd_product = f"{url_base}/{product_id}"
    response = requests.put(url_upd_product, headers=headers, data=json.dumps(product_data))
    if response.status_code == 200:
        print(response.status_code)
        print("product correctly updated!")
    else:
        print("product failed to update")
        print(response.json())

    url_upd_variant = f"{url_upd_product}/variants/{variant_id}"
    response = requests.put(url_upd_variant, headers=headers, data=json.dumps(variant_data))
    print(response.status_code)
    if response.status_code == 200:
        print("variant correctly updated!")
    else:
        print("variant failed to update")
        print(response.json())

    url_upd_image = f"{url_upd_product}/images"
    response = requests.get(url_upd_image, headers=headers)
    product_images = response.json()
    for p_image in product_images:
        id = p_image['id']
        response = requests.delete(f"{url_upd_image}/{id}", headers=headers)
        if response.status_code != 200:
            print(f"error deleting image {id}")
            print(response.json())
        print("image deleted correctly")


    for image in images:
        response = requests.post(url_upd_image, headers=headers, data=json.dumps(image))
        if response.status_code == 201:
            print("image correctly loaded")
        else:
            print(f"image failed to load : {response.text}")

    data = {
            "attribute_id": attribute_id,
            "product_id": product_id, 
            "variant_id": variant_id,
            "response": "producto actualizado correctamente",
            "updated_at": datetime.now()}
    load_tienda_nube_product_status(data)


###==========================DELETE=================================##
def tienda_nube_delete_item(item_id):

    url_base, headers = aux_base_url()
    product_data, variant_data, attribute_id, product_id, variant_id = aux_format_data(item_id,None)
    data = {"attribute_id": attribute_id}
    del_url = f"{url_base}/{product_id}"
    response = requests.delete(del_url, headers=headers)
    if response.status_code == 200:
        print("product correctly deleted!")
        delete_tienda_nube_product_status(data)
    else:
        print("product failed to delete")
        data = {
            "attribute_id": attribute_id,
            "product_id": product_id, 
            "variant_id": variant_id,
            "response": str(response.json()),
            "updated_at": datetime.now()}
        load_tienda_nube_product_status(data)
