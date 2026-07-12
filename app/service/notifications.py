import requests
from app.utils.logger import logger
def enviar_mensaje_whapi(token, telefono, mensaje):

    url = "https://gate.whapi.cloud/messages/text"
    payload = {
        "to": f"{telefono}",
        "body": mensaje
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {token}"
    }
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        logger.info(f"Whapi Response was sent.")

    

    