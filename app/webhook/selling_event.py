from app.utils.logger import logger
from flask import Blueprint, request, Response, jsonify
from app.service.pipe_selling import pipeline_selling

# BLUEPRINT CREATION
meli_sell = Blueprint("wh_sell", __name__, url_prefix="/webhooks/sells")
@meli_sell.route("", methods=["POST"], strict_slashes=False)
def main():
    data = request.json
    if data.get('topic') == 'orders_v2':
        order_id = data.get('resource').split("/")[3]
        pipeline_selling(order_id)