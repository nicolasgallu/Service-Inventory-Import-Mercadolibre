"""Resolve an order's items to internal products — one module, any platform.

Per platform we get each item's sku/gtin (tnube: already in the order
payload; meli: fetch each item from the API). Then we match those codes
against inventory.products for the business and return the internal_code
that stock systems (Bitcram) need.
"""

import requests
from app.db.helpers import get_one
from app.integrations.core.credentials import get_access_token
from app.utils.logger import logger

MELI_BASE_URL = "https://api.mercadolibre.com"
CREDENTIALS_TABLE = "platform_accounts.credentials"
PRODUCTS_TABLE = "inventory.products"


def resolve_items(platform, account, order):
    """Return [{product_id, internal_code, quantity, unit_price}] for the order."""
    # 1. Get each item's (sku, gtin, quantity, unit_price) per platform.
    if platform == "tiendanube":
        raw_items = _tnube_items(order)
    elif platform == "mercadolibre":
        raw_items = _meli_items(account, order)
    else:
        logger.warning("Unknown platform %s; no items", platform)
        return []

    # 2. Match sku/gtin against the business's products -> internal items.
    items = []
    for raw in raw_items:
        product = _match_product(account["business_id"], raw["sku"], raw["gtin"])
        if product is None:
            logger.warning(
                "No product for business %s sku=%s gtin=%s; skipping",
                account["business_id"], raw["sku"], raw["gtin"],
            )
            continue
        items.append({
            "product_id": product["id"],
            "internal_code": product["internal_code"],
            "quantity": raw["quantity"],
            "unit_price": raw["unit_price"],
        })
    return items


def _tnube_items(order):
    """Tnube's order payload already carries every product's sku."""
    items = []
    for product in order.get("products") or []:
        items.append({
            "sku": product.get("sku"),
            "gtin": None,
            "quantity": product.get("quantity"),
            "unit_price": product.get("price"),
        })
    return items


def _meli_items(account, order):
    """Meli's order only carries meli_id, so fetch each item for sku/gtin."""
    token = get_access_token(account['id']).get('access_token')
    items = []
    for order_item in order.get("order_items", []):
        meli_id = order_item.get("item", {}).get("id")
        item = _fetch_meli_item(token, meli_id)

        # GTIN lives in the item's attributes (absent for SKU-only items).
        gtin = None
        for attr in item.get("attributes", []):
            if attr.get("id") == "GTIN":
                gtin = attr.get("value_name")
                break

        items.append({
            "sku": item.get("seller_sku"),
            "gtin": gtin,
            "quantity": order_item.get("quantity"),
            "unit_price": order_item.get("unit_price"),
        })
    return items



def _fetch_meli_item(token, meli_id):
    url = MELI_BASE_URL + "/items/" + str(meli_id)
    response = requests.get(
        url,
        headers={"Authorization": "Bearer " + token},
        params={"include_attributes": "all"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def _match_product(business_id, sku, gtin):
    sql = (
        "SELECT id, internal_code FROM " + PRODUCTS_TABLE
        + " WHERE business_id = :business_id"
        + " AND (sku = :sku OR gtin = :gtin)"
        + " LIMIT 1"
    )
    try:
        return get_one(sql, {"business_id": business_id, "sku": sku, "gtin": gtin})
    except LookupError:
        return None