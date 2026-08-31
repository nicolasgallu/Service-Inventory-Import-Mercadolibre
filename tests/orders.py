import requests

url = "http://127.0.0.1:8080/webhooks/sells"


payload = {
    "id": 123456789,
    "topic": "orders_v2",
    "resource": "/orders/2000018193032192",
    "user_id": 3644237316,
    "application_id": 123456789,
    "attempts": 1,
    "sent": "2026-07-29T16:05:42.123Z",
    "received": "2026-07-29T16:05:42.456Z"
}

r = requests.post(url, json=payload)
print(r.status_code, r.json())