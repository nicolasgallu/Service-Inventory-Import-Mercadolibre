from flask import Blueprint, request, jsonify
from app.integrations.core.credentials import get_account_owner, UnknownAccount
from app.db.claims import claim, finish, fail
from app.pipelines.sells import process_order
from app.utils.logger import logger

from app.integrations.mercadolibre.orders import (
    fetch_order as fetch_meli_order,
    derive_event_type as derive_meli_event_type,
)
from app.integrations.tiendanube.orders import (
    fetch_order as fetch_tnube_order,
    derive_event_type as derive_tnube_event_type,
)

sells = Blueprint("wh_sell", __name__, url_prefix="/webhooks/sells")


@sells.route("", methods=["POST"], strict_slashes=False)
def main():
    """Router: detect the platform from the payload shape."""
    data = request.json

    # Meli sends topic=orders_v2
    if data.get("topic") == "orders_v2":
        return _handle_meli(data)

    # Tiendanube sends store_id
    if "store_id" in data:
        return _handle_tnube(request, data)

    return jsonify({"status": "ignored", "message": "not an order"}), 200


def _handle_meli(data):
    """Prepare a Meli notification: ids -> account -> order -> event type."""

    # 1. Extract ids from the payload.
    user_id = data.get("user_id")
    order_id = _order_id_from_resource(data.get("resource"))
    if not order_id:
        return jsonify({"status": "ignored", "message": "missing order id"}), 200

    # 2. Which account owns this user_id? Unknown -> ack and stop.
    try:
        account = get_account_owner(user_id, "mercadolibre")
    except UnknownAccount:
        logger.warning("Unknown Meli user_id %s; ignoring", user_id)
        return jsonify({"status": "ignored", "message": "unknown account"}), 200

    # 3. Fetch the real order (before claiming: no side effect yet).
    #    Fail -> 500 so Meli retries later.
    try:
        order = fetch_meli_order(account, order_id)
    except Exception as exc:
        logger.error("Failed to fetch Meli order %s: %s", order_id, exc)
        return jsonify({"status": "error", "message": "fetch failed"}), 500

    # 4. Derive the claim key from the REAL status (paid/cancelled).
    #    Not actionable -> ack and stop.
    event_type = derive_meli_event_type(order)
    if event_type is None:
        logger.info("Meli order %s not actionable; ignoring", order_id)
        return jsonify({"status": "ignored", "message": "status not actionable"}), 200

    # 5. Everything ready: hand over to the shared claim+run tail.
    return _claim_and_run(account, "mercadolibre", event_type, order_id, order)


def _handle_tnube(request, data):
    """Prepare a Tiendanube notification (same steps, tnube shapes)."""

    # 1. Verify the signature (placeholder until the app secret exists).
    if not _verify_tnube_hmac(request):
        return jsonify({"status": "error", "message": "invalid signature"}), 401

    # 2. Extract ids from the payload.
    store_id = data.get("store_id")
    order_id = data.get("id")
    if not order_id:
        return jsonify({"status": "ignored", "message": "missing order id"}), 200

    # 3. Which account owns this store? Unknown -> ack and stop.
    try:
        account = get_account_owner(store_id, "tiendanube")
    except UnknownAccount:
        logger.warning("Unknown tnube store_id %s; ignoring", store_id)
        return jsonify({"status": "ignored", "message": "unknown account"}), 200

    # 4. Fetch the real order (before claiming). Fail -> 500 so it retries.
    try:
        order = fetch_tnube_order(account, order_id)
    except Exception as exc:
        logger.error("Failed to fetch tnube order %s: %s", order_id, exc)
        return jsonify({"status": "error", "message": "fetch failed"}), 500

    # 5. Derive the claim key from payment_status/status.
    event_type = derive_tnube_event_type(order)
    if event_type is None:
        logger.info("Tnube order %s not actionable; ignoring", order_id)
        return jsonify({"status": "ignored", "message": "status not actionable"}), 200

    # 6. Same shared tail as Meli, different source key.
    return _claim_and_run(account, "tiendanube", event_type, order_id, order)



def _claim_and_run(account, source, event_type, order_id, order):
    """Shared tail for both platforms: claim -> run -> finish/fail."""

    # 1. Claim: only ONE worker gets to run this event (the fast-ack gate).
    event_id = claim(account["id"], source, event_type, order_id, order)
    if event_id is None:
        return jsonify({"status": "in_flight", "message": "already processing"}), 200

    # 2. Run the state machine synchronously.
    try:
        process_order(account, event_type, order_id, order)
    except Exception:
        # 3. Fail -> 500 so the platform retries (the claim re-arms it).
        fail(event_id)
        logger.exception("Order processing failed for %s", order_id)
        return jsonify({"status": "failed"}), 500

    # 4. Success -> mark done.
    finish(event_id)
    return jsonify({"status": "done"}), 200


def _verify_tnube_hmac(request):
    # TODO next step: verify x-linkedstore-hmac-sha256 against the store's
    # app secret (raw body, hex, constant-time compare).
    logger.warning("Tnube HMAC not verified yet (no secret configured)")
    return True


def _order_id_from_resource(resource):
    # Meli resource looks like "/orders/123456" -> return "123456".
    if not resource:
        return None
    parts = resource.split("/")
    return parts[2] if len(parts) >= 3 else None