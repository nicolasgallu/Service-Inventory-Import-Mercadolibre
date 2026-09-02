import json
from sqlalchemy import text
from app.db.engine import engine
from app.db.helpers import get_one
from app.integrations.core.stock_sync import StockSyncError, post_stock_movement
from app.integrations.core.order_items import resolve_items
from app.settings.config import SCHEMA_INVENTORY, SCHEMA_MERCADOLIBRE, SCHEMA_TIENDANUBE
from app.utils.logger import logger

STOCK_MOVEMENTS_TABLE = SCHEMA_INVENTORY + ".stock_movements"
BUSINESSES_TABLE = "platform_accounts.businesses"

LOCK_TIMEOUT = 30


def process_order(account, event_type, order_id, order):
    """Front door: lock the order, read its state, apply the transition."""

    # AUTOCOMMIT: each statement commits immediately, because the stock-sync
    # POST in the middle is external and can't be rolled back with a DB txn.
    conn = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
    try:
        # 1. Serialize this order (paid vs cancelled can't interleave).
        _acquire_lock(conn, account["id"], order_id)
        # 2. Read where the state machine is now: None / 'paid' / 'cancelled'.
        current = _current_status(conn, account, order_id)
        # 3. Decide and act (write the state + sync stock).
        _transition(conn, account, event_type, order_id, order, current)
    finally:
        # 4. Always release the lock, even if something above blew up.
        _release_lock(conn, account["id"], order_id)
        conn.close()


def _transition(conn, account, event_type, order_id, order, current):
    """Route to the right handler based on the claim key."""
    if event_type == "order_paid":
        _handle_paid(conn, account, order_id, order, current)
    else:
        _handle_cancelled(conn, account, order_id, order, current)


def _handle_paid(conn, account, order_id, order, current):
    """A paid delivery: sell it (or block / re-heal)."""
    # 1. Re-sell protection: a cancelled order must never sell again.
    if current == "cancelled":
        logger.info("Order %s was cancelled; blocking re-sell", order_id)
        return
    # 2. First time paid -> write the state.
    if current != "paid":
        _set_status(conn, account, order_id, "paid", order)
    # 3. Always sync: first run posts; a re-run re-attempts failed items.
    _sync_items(conn, account, order_id, order, "sale")


def _handle_cancelled(conn, account, order_id, order, current):
    """A cancelled delivery: reverse (or record / re-heal)."""
    # 1. Was paid -> flip to cancelled and reverse the stock.
    if current == "paid":
        _set_status(conn, account, order_id, "cancelled", order)
        _sync_items(conn, account, order_id, order, "reversal")
        return
    # 2. Already cancelled -> re-attempt failed reversals (self-heal).
    if current == "cancelled":
        _sync_items(conn, account, order_id, order, "reversal")
        return
    # 3. Never seen -> record the cancellation, nothing to reverse.
    _set_status(conn, account, order_id, "cancelled", order)
    logger.info("Order %s cancelled before any sale; recording only", order_id)


def _sync_items(conn, account, order_id, order, direction):
    """Sync every sold item in one direction (sale or reversal)."""
    # Each platform parses its own payload shape into the same item dicts.
    items = resolve_items(account["platform"], account, order)
    for item in items:
        _sync_one(conn, account, order_id, item, direction)


def _sync_one(conn, account, order_id, item, direction):
    """Sync ONE item exactly once (post provider, record the outcome)."""
    # 1. Reversals only when the sale actually posted.
    if direction == "reversal":
        sale_status = _stock_status(conn, account["id"], order_id, item["product_id"], "sale")
        if sale_status != "posted":
            return
    # 2. Open the movement row (or re-arm it) as 'attempting'.
    _mark_attempting(conn, account["id"], order_id, item, direction)
    # 3. Already done (posted / failed_ambiguous)? -> stop.
    status = _stock_status(conn, account["id"], order_id, item["product_id"], direction)
    if status in ("posted", "failed_ambiguous"):
        return
    # 4. Do the real work and record the outcome.
    _post_and_record(conn, account, order_id, item, direction)


def _post_and_record(conn, account, order_id, item, direction):
    """One external stock-sync POST, then write the outcome to the ledger."""
    # 1. Reversals post negative quantities.
    signed_quantity = item["quantity"] if direction == "sale" else -item["quantity"]
    # 2. Provider comes from the business config (bitcram / none / future).
    config = _business_config(account)
    provider_config = config.get("stock_sync") or {"provider": "none", "config": {}}
    try:
        # 3. The actual post.
        doc_id = post_stock_movement(provider_config, item["internal_code"], signed_quantity, item["unit_price"])
    except StockSyncError as exc:
        # 4a. Definitive rejection -> 'failed' (auto-retry next delivery).
        _set_stock_status(conn, account["id"], order_id, item["product_id"], direction, "failed", error_message=str(exc))
        logger.error("Stock sync rejected order %s product %s", order_id, item["product_id"])
        return
    except Exception as exc:
        # 4b. Timeout/5xx -> 'failed_ambiguous' (manual only, avoid double post).
        _set_stock_status(conn, account["id"], order_id, item["product_id"], direction, "failed_ambiguous", error_message=str(exc))
        logger.error("Ambiguous stock sync failure for order %s product %s", order_id, item["product_id"])
        return
    # 4c. Success -> 'posted' + the provider's doc id.
    _set_stock_status(conn, account["id"], order_id, item["product_id"], direction, "posted", doc_id)
    logger.info("Posted doc %s for order %s product %s", doc_id, order_id, item["product_id"])


def _mark_attempting(conn, account_id, order_id, item, direction):
    """Open (or re-arm) the movement row as 'attempting'.

    One row per (account, order, product, direction): first time inserts;
    duplicates only re-arm failed/attempting — never touch posted.
    """
    conn.execute(
        text(
            "INSERT INTO " + STOCK_MOVEMENTS_TABLE
            + " (account_id, order_id, product_id, direction, quantity, unit_price, status)"
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
    """Read the current status of one movement (None = not opened yet)."""
    result = conn.execute(
        text(
            "SELECT status"
            " FROM " + STOCK_MOVEMENTS_TABLE
            + " WHERE account_id = :account_id"
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
    """Write the outcome (status + doc id + error message) to the ledger."""
    conn.execute(
        text(
            "UPDATE " + STOCK_MOVEMENTS_TABLE
            + " SET status = :status, provider_doc_id = :doc_id, error_message = :error_message"
            + " WHERE account_id = :account_id"
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
    """Load and parse the business's config JSON (stock_sync, future keys)."""
    sql = "SELECT config FROM " + BUSINESSES_TABLE + " WHERE id = :business_id"
    row = get_one(sql, {"business_id": account["business_id"]})
    raw = row.get("config")
    if raw is None:
        return {}
    if isinstance(raw, str):
        return json.loads(raw)
    return raw


def _orders_table(account):
    """Each platform keeps its own orders table (different payload shapes)."""
    platform = account["platform"]
    if platform == "mercadolibre":
        return SCHEMA_MERCADOLIBRE + ".orders"
    if platform == "tiendanube":
        return SCHEMA_TIENDANUBE + ".orders"
    raise Exception("Unknown platform: " + str(platform))


def _current_status(conn, account, order_id):
    """Where is the order state machine now? (None / 'paid' / 'cancelled')"""
    table = _orders_table(account)
    result = conn.execute(text(
        "SELECT status FROM " + table
        + " WHERE account_id = :account_id AND order_id = :order_id LIMIT 1"
    ), {"account_id": account["id"], "order_id": str(order_id)})
    row = result.fetchone()
    return row[0] if row else None


def _set_status(conn, account, order_id, status, order):
    """Write (or transition) the order's state, storing the raw payload."""
    table = _orders_table(account)
    # Each platform's payload key: Meli=order_items, Tnube=products.
    if account["platform"] == "tiendanube":
        data = json.dumps(order.get("products", []))
    else:
        data = json.dumps(order.get("order_items", []))
    conn.execute(
        text(
            "INSERT INTO " + table
            + " (order_id, account_id, status, data)"
            + " VALUES (:order_id, :account_id, :status, :data)"
            + " ON DUPLICATE KEY UPDATE"
            + " status = :status"
        ),
        {
            "order_id": str(order_id),
            "account_id": account["id"],
            "status": status,
            "data": data
        }
    )


def _acquire_lock(conn, account_id, order_id):
    """Per-order mutex: serializes paid vs cancelled for the same order."""
    lock_name = "order-" + str(account_id) + "-" + str(order_id)
    result = conn.execute(text("SELECT GET_LOCK(:name, :timeout)"),
                          {"name": lock_name, "timeout": LOCK_TIMEOUT})
    if result.scalar() != 1:
        raise Exception("Could not acquire lock for order " + str(order_id))


def _release_lock(conn, account_id, order_id):
    """Release the per-order lock (closing the conn would also release it)."""
    lock_name = "order-" + str(account_id) + "-" + str(order_id)
    conn.execute(text("SELECT RELEASE_LOCK(:name)"), {"name": lock_name})