import requests
import uuid
url = "http://127.0.0.1:8080/webhooks/publications"

#test prepublish

payload = {
    "ecommerce_account_id": 1,
    "source": "internal",
    "event_type": "pre-publish",
    "external_id": str(uuid.uuid4()),
    "product_id": 1,
    "secret": "mati-gordo",
}

#test event_type: publish/update/pause/delete
payload = {
    "ecommerce_account_id": 1,
    "source": "internal",
    "event_type": "delete",
    "external_id": str(uuid.uuid4()),
    "product_id": 1,
    "secret": "mati-gordo",
}

requests.post(url=url, json=payload)

