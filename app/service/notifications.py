import time
import requests
from requests.exceptions import RequestException
from app.utils.logger import logger


def enviar_mensaje_whapi(token, telefono, mensaje):
    url = "https://gate.whapi.cloud/messages/text"

    payload = {
        "to": telefono,
        "body": mensaje
    }

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {token}"
    }

    for attempt in range(2):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=15
            )

            response.raise_for_status()
            logger.info(f"Whapi message sent to {telefono}.")
            return response

        except RequestException as e:
            if attempt == 0:
                logger.warning(
                    f"Error sending Whapi message to {telefono}. "
                    f"Retrying once... Error: {e}"
                )
                time.sleep(1)
            else:
                logger.exception(
                    f"Failed to send Whapi message to {telefono} after retry: {e}"
                )
                raise