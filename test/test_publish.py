import requests

url = "http://127.0.0.1:8080/webhooks/publications"

##LIMPIAR DATA DE TNUBE TEST EN PRODU DE EMIL...

id = 199738

publishtnube = {
    "site":"tienda-nube",
    "event_type":"publish",
    "item_id": id,
    "secret":"mati-gordo"}

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

var = ['LEFT JOIN tienda_nube.attributes as b on b.item_id = a.id', 
 'LEFT JOIN tienda_nube.product_status as c on b.attribute_id = c.attribute_id', 
 'LEFT JOIN tienda_nube.categories as d on d.category_name = a.product_type_path']


var2 = ','.join(var)
print(var2)

requests.post(url=url, json=publishtnube)

