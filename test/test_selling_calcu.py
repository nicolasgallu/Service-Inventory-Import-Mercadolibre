import requests

url = "http://127.0.0.1:8080/webhooks/selling_calculation"

id = 183807 

calculate = {
    "item_id": id,
    "secret":"mati-gordo"}

requests.post(url=url, json=calculate)