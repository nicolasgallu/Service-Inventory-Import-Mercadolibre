from app.utils.logger import logger
from flask import Blueprint, request, Response, jsonify
from app.service.pipe_selling import pipeline_selling
import threading

# BLUEPRINT CREATION
meli_sell = Blueprint("wh_sell", __name__, url_prefix="/webhooks/sells")
@meli_sell.route("", methods=["POST"], strict_slashes=False)
def main():
    data = request.json

    if 'topic' in data:
        if data.get('topic') == 'orders_v2':
            order_id = data.get('resource').split("/")[2]
            thread = threading.Thread(target=pipeline_selling, args=(order_id, 'mercadolibre'))
            thread.start()
            return jsonify({"status": "accepted", "message": "Meli Selling Event"}), 202
    elif 'store_id' in data:
        order_id = data.get('id')
        thread = threading.Thread(target=pipeline_selling, args=(order_id, 'tienda_nube'))
        thread.start()
        return jsonify({"status": "accepted", "message": "TiendaNube Selling Event"}), 202

    else:
        return jsonify({"status": "ignores", "message": "message wasnt a sell"}), 200
    
