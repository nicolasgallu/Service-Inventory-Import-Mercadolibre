from flask import Blueprint, request, jsonify
from app.db.claims import claim, fail, finish
from app.pipelines.publish import pipeline_publish
from app.utils.logger import logger
from app.settings.config import SECRET_GUIAS

publications = Blueprint("wh_publish", __name__, url_prefix="/webhooks/publications")
@publications.route("", methods=["POST"], strict_slashes=False)
def main():
    payload = request.json
    if SECRET_GUIAS != payload['secret']:
        return jsonify({"status": "not accepted"}), 400

    business_id = payload.get('business_id')
    source = payload.get('source')
    event_type = payload.get('event_type')
    external_id = payload.get('id') ##modify name
    stored = {k: v for k, v in payload.items() if k != "secret"}

    event_id = claim(ecommerce_account_id, source, event_type, external_id, stored)

    if event_id is None:
        # Someone else is already processing this exact request.
        return jsonify({"status": "in_flight"}), 200
    
    try:
        pipeline_publish(payload)
    except Exception:
        fail(event_id)
        logger.exception("publish failed for %s", id)
        return jsonify({"status": "failed"}), 500

    finish(event_id)
    return jsonify({"status": "done"}), 200