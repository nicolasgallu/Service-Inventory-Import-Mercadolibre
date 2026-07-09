import requests

url = "http://127.0.0.1:8080/webhooks/publications"

id = 183807 

publish = {
    "event_type":"publish",
    "item_id": id,
    "secret":"mati-gordo"}

pre_publish = {
    "event_type":"pre-publish",
    "item_id": id,
    "secret":"mati-gordo"}

delete = {
    "event_type":"delete",
    "item_id": id,
    "secret":"mati-gordo"}


requests.post(url=url, json=publish)

