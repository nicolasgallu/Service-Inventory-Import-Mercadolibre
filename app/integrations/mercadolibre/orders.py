import requests
from app.db.helpers import get_one
from app.settings.config import SCHEMA_ACCOUNTS,SCHEMA_INVENTORY, SCHEMA_MERCADOLIBRE
from app.utils.logger import logger


PRODUCT_LISTINGS_TABLE = SCHEMA_MERCADOLIBRE + ".product_listings"
PRODUCTS_TABLE = SCHEMA_INVENTORY + ".products"
CREDENTIALS_TABLE = SCHEMA_ACCOUNTS + ".credentials"

MELI_BASE_URL = "https://api.mercadolibre.com"


def get_access_token(account_id):
    """Read the account's current Meli token from the credentials table."""
    sql = (
        "SELECT access_token FROM " + CREDENTIALS_TABLE
        + " WHERE ecommerce_account_id = :account_id"
    )
    row = get_one(sql, {"account_id": account_id})
    return row["access_token"]


def fetch_order(account, order_id):
    """Fetch one order from MercadoLibre for the given account.

    Raises on any non-2xx (the webhook will turn that into a 500 retry).
    """
    token = get_access_token(account["id"])
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



def resolve_order_items(account, order):
    """Turn a Meli order's order_items into internal items.

    Returns a list of {product_id, quantity, unit_price}. Items whose
    meli_id cannot be resolved to this account's product are skipped.
    """
    items = []
    for order_item in order.get("order_items", []):
        meli_id = order_item.get("item", {}).get("id")
        data = _resolve_product_id(account, meli_id)
        if data is None:
            logger.warning(
                "Could not resolve meli_id %s for account %s; skipping",
                meli_id, account["id"],
            )##informar por WPP
            continue
        items.append({
            "product_id": data["product_id"],
            "internal_code": data["internal_code"],
            "quantity": order_item.get("quantity"),
            "unit_price": order_item.get("unit_price"),
        })
    return items


def _resolve_product_id(account, meli_id):
    """Map a Meli listing id to this account's internal product id.

    Returns None when the listing is unknown for this account.
    """
    sql = (
        "SELECT pl.product_id, p.internal_code FROM " + PRODUCT_LISTINGS_TABLE + " pl"
        " JOIN " + PRODUCTS_TABLE + " p ON p.id = pl.product_id"
        " WHERE pl.meli_id = :meli_id AND p.ecommerce_account_id = :account_id"
        " LIMIT 1"
    )
    try:
        return get_one(sql, {
            "meli_id": str(meli_id),
            "account_id": account["id"],
        })
    except LookupError:
        return None