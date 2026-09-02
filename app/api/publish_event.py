import hashlib
import hmac
from flask import Blueprint, request, jsonify
from app.db.claims import claim, fail, finish
from app.pipelines.publish import pipeline_publish
from app.utils.logger import logger
from app.db.helpers import get_one
from app.settings.config import SCHEMA_ACCOUNTS, SCHEMA_INVENTORY


publications = Blueprint("wh_publish", __name__, url_prefix="/webhooks/publications")
@publications.route("", methods=["POST"], strict_slashes=False)
def main():
    raw_body = request.get_data()
    payload = request.get_json(force=True)

    expected = _expected_signature(payload, raw_body)
    if expected is None or not hmac.compare_digest(request.headers.get("X-Signature", ""), expected):
        return jsonify({"status": "unauthorized"}), 401

    error = _validate_publication(payload)
    if error:
        return jsonify({"status": "rejected", "message": error}), 400

    account_id = payload.get('account_id')
    source = payload.get('source')
    event_type = payload.get('event_type')
    external_id = payload.get('id')
    stored = {k: v for k, v in payload.items() if k != "secret"}

    event_id = claim(account_id, source, event_type, external_id, stored)

    if event_id is None:
        # Someone else is already processing this exact request.
        return jsonify({"status": "in_flight"}), 200
    
    try:
        pipeline_publish(payload)
    except Exception:
        fail(event_id)
        logger.exception("publish failed for event %s (external id %s)", event_id, external_id)
        return jsonify({"status": "failed"}), 500

    finish(event_id)
    return jsonify({"status": "done"}), 200


def _validate_publication(payload):
    account_id = payload.get('account_id')
    product_id = payload.get('product_id')

    if not account_id or not product_id:
        return "missing account_id or product_id"

    try:
        account = get_one(
            "SELECT business_id, platform FROM " + SCHEMA_ACCOUNTS + ".accounts WHERE id = :id",
            {"id": account_id})
    except LookupError:
        return "unknown account"

    try:
        product = get_one(
            "SELECT business_id FROM " + SCHEMA_INVENTORY + ".products WHERE id = :id",
            {"id": product_id})
    except LookupError:
        return "unknown product"

    if account["business_id"] != product["business_id"]:
        return "product does not belong to this business"

    target = payload.get('target')
    if target and account["platform"] != target:
        return "account platform does not match target"

    return None


def _expected_signature(payload, raw_body):
    account_id = payload.get("account_id")
    if not account_id:
        return None
    try:
        row = get_one(
            "SELECT b.webhook_secret AS secret FROM " + SCHEMA_ACCOUNTS + ".accounts a "
            "JOIN " + SCHEMA_ACCOUNTS + ".businesses b ON b.id = a.business_id "
            "WHERE a.id = :account_id",
            {"account_id": account_id})
    except LookupError:
        return None
    if not row["secret"]:
        return None
    return hmac.new(row["secret"].encode(), raw_body, hashlib.sha256).hexdigest()