import json
import requests
from sqlalchemy import text
from app.utils.logger import logger
from app.settings.config import SCHEMA_MERCADOLIBRE
from app.integrations.core.credentials import get_access_token
from app.integrations.mercadolibre.product_handler import get_data_for_meli
from app.db.engine import engine

MELI_API = "https://api.mercadolibre.com"
COSTS_TABLE = f"{SCHEMA_MERCADOLIBRE}.selling_costs"
DEFAULT_DIMENSIONS = "30x30x30,1000"  # LxWxH,peso_en_gramos


def _flatten_settings(settings_json):
    """attributes.settings (JSON) -> {VARIABLE_ID: user_input_value}."""
    values = {}
    for group in json.loads(settings_json or "[]"):
        for variables in group.values():
            for variable in variables or []:
                values[variable.get("id")] = variable.get("user_input_value")
    return values


def _to_bool(value):
    return str(value).strip().lower() in ("true", "1", "si", "yes")


def _weight_from_dimensions(dimensions):
    """'30x30x30,1000' -> 1000 (peso en gramos)."""
    try:
        return int(str(dimensions).split(",")[-1])
    except (ValueError, IndexError):
        return 1000


def _meli_get(path, token, params=None):
    """GET con bearer token; lanza excepción ante errores HTTP."""
    response = requests.get(
        MELI_API + path,
        params=params or {},
        headers={"Authorization": f"Bearer {token}"},
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def calculate_cost(payload):
    """Estima el costo de vender en MeLi Argentina: comisión + envío."""
    logger.info("Running Cost Calculation Action")

    account_id = payload.get("account_id")
    product_id = payload.get("product_id")
    token = get_access_token(account_id).get("access_token")

    item_data = get_data_for_meli(product_id)
    product_listing_id = item_data.get("product_listing_id")
    price = item_data.get("price_meli") or item_data.get("price")
    category_id = item_data.get("category_id")
    condition_type = item_data.get("condition_type")
    currency_id = item_data.get("currency_id") or "ARS"
    dimensions = item_data.get("dimensions") or DEFAULT_DIMENSIONS

    if not price or not category_id:
        logger.error("Cannot calculate cost for product %s: missing price/category", product_id)
        return None

    settings = _flatten_settings(item_data.get("settings"))
    listing_type = settings.get("LISTING_TYPE")
    shipping_mode = settings.get("MODE")
    logistic_type = settings.get("LOGISTIC_TYPE")
    free_shipping = _to_bool(settings.get("FREE_SHIPPING"))

    # ---- 1. Comisión por venta --------------------------------------------
    fee_data = _meli_get("/sites/MLA/listing_prices", token, {
        "category_id": category_id,
        "price": price,
        "cy_id": currency_id,
        "logistic_type": logistic_type,
        "shipping_modes": shipping_mode,
        "listing_type_id": listing_type,
        "billable_weight": _weight_from_dimensions(dimensions),
    })
    sale_fee = fee_data.get("sale_fee_details", {})
    listing_fee = fee_data.get("listing_fee_details", {})
    fee_tax = fee_data.get("fee_tax", 0)  # IVA sobre comisiones (21 en AR)

    # ---- 2. Costo de envío --------------------------------------------------
    user_id = _meli_get("/users/me", token).get("id")
    ship_data = _meli_get(f"/users/{user_id}/shipping_options/free", token, {
        "dimensions": dimensions,
        "verbose": "true",
        "item_price": price,
        "category_id": category_id,
        "listing_type_id": listing_type,
        "mode": shipping_mode,
        "condition": condition_type,
        "logistic_type": logistic_type,
        "free_shipping": str(free_shipping).lower(),
    })
    country = ship_data.get("coverage", {}).get("all_country", {})
    discount = country.get("discount", {})

    # ---- 3. Total -------------------------------------------------------------
    cost = {
        "sale_fee_amount": fee_data.get("sale_fee_amount", 0),           # comisión total, sin IVA
        "sale_fixed_fee": sale_fee.get("fixed_fee", 0),                  # componente fijo ARS
        "financing_add_on_fee": sale_fee.get("financing_add_on_fee", 0), # % extra si hay cuotas
        "meli_percentage_fee": sale_fee.get("meli_percentage_fee", 0),   # % comisión MeLi
        "percentage_fee": sale_fee.get("percentage_fee", 0),             # % total aplicado
        "gross_amount": sale_fee.get("gross_amount", price),             # precio base del cálculo
        "listing_fixed_fee": listing_fee.get("fixed_fee", 0),            # costo de publicar
        "listing_gross_amount": listing_fee.get("gross_amount", 0),
        "fee_tax": fee_tax,
        "ship_list_cost": country.get("list_cost", 0),                   # envío sin beneficio
        "ship_discount_rate": discount.get("rate", 0),                   # % que subsidia MeLi
        "ship_promoted_amount": discount.get("promoted_amount", 0),      # envío que pagás vos
    }
    # Lo que realmente pagás: comisión + envío ya descontado (IVA aparte)
    cost["total_selling_cost"] = round(
        cost["sale_fee_amount"] + cost["ship_promoted_amount"], 2
    )
    cost["total_selling_cost_with_tax"] = round(
        cost["total_selling_cost"] * (1 + fee_tax / 100), 2
    )

    _save_cost(product_listing_id, price, cost, fee_data, ship_data)
    return cost


def _save_cost(product_listing_id, price, cost, fee_data, ship_data):
    """Reemplaza el snapshot de costos de la publicación en una transacción."""
    api_payload = json.dumps({
        "listing_prices": fee_data,
        "shipping_options": ship_data,
    })
    row = {
        "listing_id": product_listing_id,
        "price": price,
        "api_payload": api_payload,
        **cost,
    }
    columns = ", ".join(row.keys())
    params = ", ".join(f":{key}" for key in row)

    with engine.begin() as conn:
        conn.execute(
            text(f"DELETE FROM {COSTS_TABLE} WHERE product_listing_id = :listing_id"),
            {"listing_id": product_listing_id},
        )
        conn.execute(
            text(f"INSERT INTO {COSTS_TABLE} ({columns}) VALUES ({params})"),
            row,
        )