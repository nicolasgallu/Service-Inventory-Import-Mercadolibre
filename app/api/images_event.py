import base64
import hashlib
import hmac

from flask import Blueprint, request, jsonify
from google.cloud import storage

from app.db.claims import claim, fail, finish
from app.utils.logger import logger
from app.db.helpers import get_one, execute
from app.settings.config import SCHEMA_ACCOUNTS, SCHEMA_INVENTORY


images = Blueprint("wh_images", __name__, url_prefix="/webhooks/images")

BUCKET_NAME = "pictures_ecommerce_guiaslocales"
MAX_IMAGES_PER_PRODUCT = 10
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@images.route("", methods=["POST"], strict_slashes=False)
def main():
    raw_body = request.get_data()
    payload = request.get_json(force=True)

    expected = _expected_signature(payload, raw_body)
    if expected is None or not hmac.compare_digest(request.headers.get("X-Signature", ""), expected):
        return jsonify({"status": "unauthorized"}), 401

    error = _validate_image(payload)
    if error:
        return jsonify({"status": "rejected", "message": error}), 400

    account_id = payload.get("account_id")
    source = payload.get("source")
    event_type = payload.get("event_type")
    external_id = payload.get("id")
    # don't store the raw file bytes in the events table
    stored = {k: v for k, v in payload.items() if k not in ("secret", "file")}

    event_id = claim(account_id, source, event_type, external_id, stored)

    if event_id is None:
        # Someone else is already processing this exact request.
        return jsonify({"status": "in_flight"}), 200

    try:
        if event_type == "create":
            result = _handle_create(payload)
        else:
            result = _handle_delete(payload)
    except Exception:
        fail(event_id)
        logger.exception("image %s failed for event %s (external id %s)", event_type, event_id, external_id)
        return jsonify({"status": "failed"}), 500

    finish(event_id)
    return jsonify({"status": "done", **result}), 200


def _validate_image(payload):
    account_id = payload.get("account_id")
    product_id = payload.get("product_id")
    event_type = payload.get("event_type")

    if not account_id or not product_id:
        return "missing account_id or product_id"

    if event_type not in ("create", "delete"):
        return "invalid event_type"

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

    if event_type == "create":
        if not payload.get("file"):
            return "missing file"
        if not _is_png(payload["file"]):
            return "file is not a png"

    if event_type == "delete":
        if not payload.get("image_id"):
            return "missing image_id"

    return None


def _handle_create(payload):
    product_id = payload["product_id"]

    row = get_one(
        "SELECT COUNT(*) AS total FROM " + SCHEMA_INVENTORY + ".product_images "
        "WHERE product_id = :product_id",
        {"product_id": product_id})

    if row["total"] >= MAX_IMAGES_PER_PRODUCT:
        # already at the limit, nothing to do
        return {}

    raw = base64.b64decode(payload["file"])
    next_number = row["total"] + 1
    blob_path = "{}/{}_{}.png".format(product_id, product_id, next_number)

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_path)
    blob.upload_from_string(raw, content_type="image/png")

    url = blob.public_url
    execute(
        "INSERT INTO " + SCHEMA_INVENTORY + ".product_images (product_id, url) "
        "VALUES (:product_id, :url)",
        {"product_id": product_id, "url": url})

    return {"url": url}


def _handle_delete(payload):
    product_id = payload["product_id"]
    image_id = payload["image_id"]

    try:
        row = get_one(
            "SELECT url FROM " + SCHEMA_INVENTORY + ".product_images "
            "WHERE id = :id AND product_id = :product_id",
            {"id": image_id, "product_id": product_id})
    except LookupError:
        # already gone, nothing to do
        return {}

    blob_path = _blob_path_from_url(row["url"], product_id)

    client = storage.Client()
    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(blob_path)
    if blob.exists():
        blob.delete()

    execute(
        "DELETE FROM " + SCHEMA_INVENTORY + ".product_images "
        "WHERE id = :id AND product_id = :product_id",
        {"id": image_id, "product_id": product_id})

    return {}


def _is_png(file_data):
    try:
        raw = base64.b64decode(file_data, validate=True)
    except Exception:
        return False
    return raw[:8] == PNG_MAGIC


def _blob_path_from_url(url, product_id):
    # url looks like: https://storage.googleapis.com/<bucket>/<product_id>/<product_id>_<n>.png
    prefix = "https://storage.googleapis.com/{}/".format(BUCKET_NAME)
    if url.startswith(prefix):
        return url[len(prefix):]
    # fallback: last two segments are product_id/filename
    parts = url.split("/")
    return "/".join(parts[-2:])


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