from flask import Blueprint, request, jsonify
from app.integrations.mercadolibre.account import resolve_account_by_meli_user, UnknownAccount
from app.integrations.mercadolibre.orders import fetch_order, derive_event_type
from app.pipelines.sells import process_order
from app.db.claims import claim, finish, fail
from app.utils.logger import logger

SOURCE = "mercadolibre"

meli_sell = Blueprint("wh_sell", __name__, url_prefix="/webhooks/sells")


@meli_sell.route("", methods=["POST"], strict_slashes=False)
def main():
    data = request.json

    # 1. Only Meli order notifications for now.
    if data.get("topic") != "orders_v2":
        return jsonify({"status": "ignored", "message": "not an order"}), 200

    user_id = data.get("user_id")
    order_id = _order_id_from_resource(data.get("resource"))
    if not order_id:
        return jsonify({"status": "ignored", "message": "missing order id"}), 200

    # 2. Which account is this for?
    try:
        account = resolve_account_by_meli_user(user_id)
    except UnknownAccount:
        logger.warning("Unknown Meli user_id %s; ignoring", user_id)
        return jsonify({"status": "ignored", "message": "unknown account"}), 200

    # 3. Fetch the order BEFORE any claim (no side effect yet).
    try:
        order = fetch_order(account, order_id)
    except Exception as exc:
        logger.error("Failed to fetch order %s: %s", order_id, exc)
        return jsonify({"status": "error", "message": "fetch failed"}), 500

    # 4. Derive the claim key from the REAL status.
    event_type = derive_event_type(order)
    if event_type is None:
        logger.info("Order %s status %s not actionable; ignoring", order_id, order.get("status"))
        return jsonify({"status": "ignored", "message": "status not actionable"}), 200

    # 5. Claim — this is the fast-ack gate.
    event_id = claim(account["id"], SOURCE, event_type, order_id, order)
    if event_id is None:
        return jsonify({"status": "in_flight", "message": "already processing"}), 200

    # 6. Run (synchronously), then finish/fail.
    try:
        process_order(account, event_type, order_id, order)
    except Exception:
        fail(event_id)
        logger.exception("Order processing failed for %s", order_id)
        return jsonify({"status": "failed"}), 500

    finish(event_id)
    return jsonify({"status": "done"}), 200


def _order_id_from_resource(resource):
    if not resource:
        return None
    parts = resource.split("/")
    return parts[2] if len(parts) >= 3 else None