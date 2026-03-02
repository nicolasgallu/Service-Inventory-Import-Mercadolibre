import requests

def enviar_mensaje_whapi(token, telefono, mensaje):
    if mensaje is None or mensaje == "":
        raise ValueError
    if isinstance(telefono, int) == False:
        raise TypeError
    
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
    res = requests.post(url, json=payload, headers=headers)
    return res.json()

    