from app.service.pipe_publish import pipeline_publish
from app.utils.logger import logger
from app.settings.config import SECRET_GUIAS
from flask import Blueprint, request, Response, jsonify

# BLUEPRINT CREATION
meli_publish = Blueprint("wh_publish", __name__, url_prefix="/webhooks/publications")
@meli_publish.route("", methods=["POST"], strict_slashes=False)
def main():
    response = request.json
    if SECRET_GUIAS != response['secret']:
        return Response(status=401)
    logger.info("Receving notification from App Import")
    pipeline_publish(response)
    return jsonify({"status": "accepted"}), 202