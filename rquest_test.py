import requests

url = "https://import-gestion-inventario-402745694567.us-central1.run.app/webhooks/goog-app/publications"

data = {
    "event_type":"publish",
    "item_id": 77464,
    "secret":"mati-gordo"}

#data = {
#    "event_type":"paused", 
#    "item_id": 77456,
#    "secret":"xxx"}
#
requests.post(url, json=data)