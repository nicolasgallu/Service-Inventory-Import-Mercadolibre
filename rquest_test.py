import requests

url = "xxx/webhooks/goog-app/publications"

data = {
    "event_type":"publish",
    "item_id": 77456,
    "secret":"xxx"}

data = {
    "event_type":"paused", 
    "item_id": 77456,
    "secret":"xxx"}

requests.post(url, json=data)