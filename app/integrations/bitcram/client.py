import json
import requests
from app.utils.logger import logger

class BitcramError(Exception):
    """A definitive Bitcram rejection (safe to retry)."""


def post_sale_doc(config, internal_code, quantity, unit_price):
    """Post ONE commercial doc to Bitcram.

    `quantity` is already signed (positive = sale, negative = reversal).
    Returns the doc id. Raises BitcramError on a definitive failure;
    any other exception means "maybe it committed" (ambiguous).
    """
    base_url = config["base_url"].rstrip("/")
    checkout_number = config["checkout_number"]
    token = config["token"]
    payment_type = config["payment_type"]
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}

    checkout = _open_checkout(base_url, checkout_number, headers)
    payment_type_id = _payment_type_id(base_url, checkout["session_id"], headers)
    doc = _commercial_doc(checkout, payment_type_id, payment_type, internal_code, quantity, unit_price)

    response = requests.post(
        base_url + "/api/commercial_docs/index",
        headers=headers, json=doc, timeout=30,
    )


    if response.status_code >= 500:
        raise requests.exceptions.RequestException("Bitcram 5xx: " + response.text)
    if response.status_code >= 400:
        raise BitcramError("Bitcram rejected doc: " + response.text)
    doc_id = response.json().get("id")
    if not doc_id:
        raise BitcramError("Bitcram response has no id")
    return doc_id


def _open_checkout(base_url, checkout_number, headers):
    response = requests.get(
        base_url + "/api/checkouts/index",
        headers=headers,
        params={"where": json.dumps({"checkouts.checkout_number": checkout_number})},
        timeout=30,
    )
    response.raise_for_status()
    items = response.json().get("items", [])
    if not items:
        raise BitcramError("No checkout for number " + str(checkout_number))
    checkout = items[0]
    if not checkout.get("is_open"):
        raise BitcramError("Checkout " + str(checkout_number) + " is closed")
    return {
        "session_id": checkout.get("last_checkout_session", {}).get("id"),
        "warehouse_id": checkout.get("warehouse", {}).get("id"),
    }


def _payment_type_id(base_url, session_id, headers):
    response = requests.get(
        base_url + "/api/checkout_sessions/index/" + str(session_id),
        headers=headers, timeout=30,
    )
    response.raise_for_status()
    accounts = response.json().get("checkout_session_accounts", [])
    if not accounts:
        raise BitcramError("No accounts for checkout session")
    payment_type_id = accounts[0].get("checkout_account", {}).get("payment_type", {}).get("id")
    if not payment_type_id:
        raise BitcramError("No payment type id for checkout session")
    return payment_type_id


def _commercial_doc(checkout, payment_type_id, payment_type, internal_code, quantity, unit_price):

    return {
        "checkout_session": {"id": checkout["session_id"]},
        "iva_condition": {"id": "CF"},
        "items": [{
            "quantity": quantity,
            "unit_price": unit_price,
            "stock_mov_item": {
                "stock_item": {
                    "product": {"id": internal_code},
                    "warehouse": {"id": checkout["warehouse_id"]},
                }
            },
        }],
        "payments": [
            {
            "amount": quantity * unit_price,
            "payment_type_id": payment_type_id,
            "payment_type": {"id": payment_type}
            }
        ]
    }