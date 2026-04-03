import threading
from app.service.pipe_calculator import calculating_cost
from app.utils.logger import logger
from app.settings.config import SECRET_GUIAS
from flask import Blueprint, request, Response, jsonify

# BLUEPRINT CREATION
wh_calculation = Blueprint("wh_calculation", __name__, url_prefix="/webhooks/selling_calculation")
@wh_calculation.route("", methods=["POST"], strict_slashes=False)
def main():
    response = request.json
    if SECRET_GUIAS != response['secret']:
        return Response(status=401)
    logger.info("Receving notification from App Import - Dispatching thread")
    thread = threading.Thread(target=calculating_cost, args=(response,))
    thread.start()
    return jsonify({"status": "accepted", "message": "Task dispatched to background"}), 202