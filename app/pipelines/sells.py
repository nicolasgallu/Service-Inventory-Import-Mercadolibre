import json
from sqlalchemy import text
from app.db.engine import engine
from app.db.helpers import get_one
from app.integrations.core.stock_sync import StockSyncError, post_stock_movement
from app.integrations.mercadolibre.orders import resolve_order_items
from app.settings.config import SCHEMA_INVENTORY, SCHEMA_MERCADOLIBRE
from app.utils.logger import logger

ORDERS_TABLE = SCHEMA_MERCADOLIBRE + ".orders"
STOCK_MOVEMENTS_TABLE = SCHEMA_INVENTORY + ".stock_movements"
BUSINESSES_TABLE = "platform_accounts.businesses"

LOCK_TIMEOUT = 30


def process_order(account, event_type, order_id, order):
    # AUTOCOMMIT: each statement commits immediately, because the stock-sync
    # POST in the middle is external and can't be rolled back with a DB txn.
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        _acquire_lock(conn, account["id"], order_id)
        current = _current_status(conn, account["id"], order_id)
        _transition(conn, account, event_type, order_id, order, current)
    finally:
        _release_lock(conn, account["id"], order_id)
        conn.close()


def _transition(conn, account, event_type, order_id, order, current):
    if event_type == "order_paid":
        _handle_paid(conn, account, order_id, order, current)
    else:
        _handle_cancelled(conn, account, order_id, order, current)


def _handle_paid(conn, account, order_id, order, current):
    if current == "cancelled":
        logger.info("Order %s was cancelled; blocking re-sell", order_id)
        return
    if current != "paid":
        _set_status(conn, account["id"], order_id, "paid", order)
    # Always sync: first run posts; a re-run re-attempts any failed items.
    _sync_items(conn, account, order_id, order, "sale")


def _handle_cancelled(conn, account, order_id, order, current):
    if current == "paid":
        _set_status(conn, account["id"], order_id, "cancelled", order)
        _sync_items(conn, account, order_id, order, "reversal")
        return
    if current == "cancelled":
        _sync_items(conn, account, order_id, order, "reversal")
        return
    _set_status(conn, account["id"], order_id, "cancelled", order)
    logger.info("Order %s cancelled before any sale; recording only", order_id)


def _sync_items(conn, account, order_id, order, direction):
    for item in resolve_order_items(account, order):
        _sync_one(conn, account, order_id, item, direction)


def _sync_one(conn, account, order_id, item, direction):
    if direction == "reversal" and not _sale_was_posted(conn, account, order_id, item):
        return
    _mark_attempting(conn, account["id"], order_id, item, direction)
    if _already_settled(conn, account, order_id, item, direction):
        return
    _post_and_record(conn, account, order_id, item, direction)


def _sale_was_posted(conn, account, order_id, item):
    status = _stock_status(conn, account["id"], order_id, item["product_id"], "sale")
    return status == "posted"


def _already_settled(conn, account, order_id, item, direction):
    status = _stock_status(conn, account["id"], order_id, item["product_id"], direction)
    return status in ("posted", "failed_ambiguous")


def _post_and_record(conn, account, order_id, item, direction):
    signed_quantity = item["quantity"] if direction == "sale" else -item["quantity"]
    provider_config = _stock_sync_config(account)
    try:
        doc_id = post_stock_movement(provider_config, item["internal_code"], signed_quantity, item["unit_price"])
    except StockSyncError as exc:
        _set_stock_status(conn, account["id"], order_id, item["product_id"], direction, "failed", error_message=exc)
        logger.error("Stock sync rejected order %s product %s", order_id, item["product_id"])
        return
    except Exception as exc:
        _set_stock_status(conn, account["id"], order_id, item["product_id"], direction, "failed_ambiguous", error_message=exc)
        logger.error("Ambiguous stock sync failure for order %s product %s", order_id, item["product_id"])
        return
    _set_stock_status(conn, account["id"], order_id, item["product_id"], direction, "posted", doc_id)
    logger.info("Posted doc %s for order %s product %s", doc_id, order_id, item["product_id"])


def _stock_sync_config(account):
    config = _business_config(account)
    return config.get("stock_sync") or {"provider": "none", "config": {}}


def _mark_attempting(conn, account_id, order_id, item, direction):
    conn.execute(
        text(
            "INSERT INTO " + STOCK_MOVEMENTS_TABLE
            + " (ecommerce_account_id, order_id, product_id, direction, quantity, unit_price, status)"
            + " VALUES (:account_id, :order_id, :product_id, :direction, :quantity, :unit_price, 'attempting')"
            + " ON DUPLICATE KEY UPDATE"
            + " status = IF(status IN ('failed', 'attempting'), 'attempting', status)"
        ),
        {
            "account_id": account_id,
            "order_id": str(order_id),
            "product_id": item["product_id"],
            "quantity": item["quantity"],
            "direction": direction,
            "unit_price": item["unit_price"],
        }
    )

def _stock_status(conn, account_id, order_id, product_id, direction):
    result = conn.execute(
        text(
            "SELECT status"
            " FROM " + STOCK_MOVEMENTS_TABLE
            + " WHERE ecommerce_account_id = :account_id"
            + " AND order_id = :order_id"
            + " AND product_id = :product_id"
            + " AND direction = :direction"
            + " LIMIT 1"
        ),
        {
            "account_id": account_id,
            "order_id": str(order_id),
            "product_id": product_id,
            "direction": direction
        }
    )
    row = result.fetchone()
    return row[0] if row else None


def _set_stock_status(conn, account_id, order_id, product_id, direction, status, doc_id=None, error_message=None):
        conn.execute(
            text(
                "UPDATE " + STOCK_MOVEMENTS_TABLE
                + " SET status = :status, provider_doc_id = :doc_id, error_message = :error_message"
                + " WHERE ecommerce_account_id = :account_id"
                + " AND order_id = :order_id"
                + " AND product_id = :product_id"
                + " AND direction = :direction"
            ),
            {
                "status": status,
                "doc_id": doc_id,
                "account_id": account_id,
                "order_id": str(order_id),
                "product_id": product_id,
                "direction": direction,
                "error_message": error_message,
            }
        )


def _business_config(account):
    sql = "SELECT config FROM " + BUSINESSES_TABLE + " WHERE id = :business_id"
    row = get_one(sql, {"business_id": account["business_id"]})
    raw = row.get("config")
    if raw is None:
        return {}
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def _current_status(conn, account_id, order_id):
    result = conn.execute(text(
        "SELECT status FROM " + ORDERS_TABLE
        + " WHERE ecommerce_account_id = :account_id AND order_id = :order_id LIMIT 1"
    ), {"account_id": account_id, "order_id": str(order_id)})
    row = result.fetchone()
    return row[0] if row else None


def _set_status(conn, account_id, order_id, status, order):
    data = json.dumps(order.get("order_items", []))
    conn.execute(
        text(
            "INSERT INTO " + ORDERS_TABLE
            + " (order_id, ecommerce_account_id, status, data)"
            + " VALUES (:order_id, :account_id, :status, :data)"
            + " ON DUPLICATE KEY UPDATE"
            + " status = :status"
        ),
        {
            "order_id": str(order_id),
            "account_id": account_id,
            "status": status,
            "data": data
        }
    )

def _acquire_lock(conn, account_id, order_id):
    lock_name = "order-" + str(account_id) + "-" + str(order_id)
    result = conn.execute(text("SELECT GET_LOCK(:name, :timeout)"),
                          {"name": lock_name, "timeout": LOCK_TIMEOUT})
    if result.scalar() != 1:
        raise Exception("Could not acquire lock for order " + str(order_id))


def _release_lock(conn, account_id, order_id):
    lock_name = "order-" + str(account_id) + "-" + str(order_id)
    conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": lock_name})