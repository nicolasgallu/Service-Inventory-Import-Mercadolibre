import requests
import uuid
url = "http://127.0.0.1:8080/webhooks/publications"

#test 
# event_type: pre-publish/publish/update/pause/delete
# source: frontend_app, internal, etc ..
# target: tiendanube, mercadolibre, all
# secret: hmac

payload = {
    "id": str(uuid.uuid4()),
    "business_id": 1,
    "source": "internal",
    "target": "all",
    "event_type": "update",
    "product_id": 3,
    "secret": "mati-gordo",
}

requests.post(url=url, json=payload)

