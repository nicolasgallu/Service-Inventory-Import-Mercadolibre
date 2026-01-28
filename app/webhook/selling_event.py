from app.utils.logger import logger
from flask import Blueprint, request, Response, jsonify

# BLUEPRINT CREATION
meli_sell = Blueprint("wh_sell", __name__, url_prefix="/webhooks/mercadolibre/sells")
@meli_sell.route("", methods=["POST"], strict_slashes=False)
def main():
    response = request.json
    logger.info(f"Notificacion de venta en Meli {response}")
