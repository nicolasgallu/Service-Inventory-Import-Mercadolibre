import requests
from app.integrations.core.credentials import get_access_token

MELI_BASE_URL = "https://api.mercadolibre.com"

def fetch_order(account, order_id):
    """Fetch one order from MercadoLibre for the given account.

    Raises on any non-2xx (the webhook will turn that into a 500 retry).
    """
    token = get_access_token(account["id"]).get('access_token')
    url = MELI_BASE_URL + "/orders/" + str(order_id)
    headers = {"Authorization": "Bearer " + token}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()


def derive_event_type(order):
    """Map the order's REAL status to our claim key.

    Returns 'order_paid', 'order_cancelled', or None (not actionable).
    """
    status = order.get("status")
    if status == "paid":
        return "order_paid"
    if status == "cancelled":
        return "order_cancelled"
    return None