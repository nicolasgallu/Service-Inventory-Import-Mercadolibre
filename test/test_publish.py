import requests

url = "http://127.0.0.1:8080/webhooks/publications"
##LIMPIAR DATA DE TNUBE TEST EN PRODU DE EMIL...

id = 205378

publishtnube = {
    "site":"tienda-nube",
    "event_type":"publish",
    "item_id": id,
    "secret":"mati-gordo"}


updatetnube = {
    "site":"tienda-nube",
    "event_type":"update",
    "item_id": id,
    "secret":"mati-gordo"}


deltnube = {
    "site":"tienda-nube",
    "event_type":"delete",
    "item_id": id,
    "secret":"mati-gordo"}



pre_publish = {
    "event_type":"pre-publish",
    "item_id": id,
    "secret":"mati-gordo"}

publish = {
    "event_type":"publish",
    "item_id": id,
    "secret":"mati-gordo"}

update = {
    "event_type":"update",
    "item_id": id,
    "secret":"mati-gordo"}

pause = {
    "event_type":"pause",
    "item_id": id,
    "secret":"mati-gordo"}

delete = {
    "event_type":"delete",
    "item_id": id,
    "secret":"mati-gordo"}

category = {
    "site":"tienda-nube",
    "event_type":"create_category",
    "name": "BELLEZA",
    "secret":"mati-gordo"}

requests.post(url=url, json=publishtnube)