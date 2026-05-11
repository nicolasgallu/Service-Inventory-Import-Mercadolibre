from app.utils.logger import logger
from flask import Blueprint, request, jsonify
from app.service.pipe_selling import pipeline_selling
import threading


def run_process(order_id, platform):
    global orders
    pipeline_selling(order_id, platform)
    orders = []
    
orders = []

meli_sell = Blueprint("wh_sell", __name__, url_prefix="/webhooks/sells")
@meli_sell.route("", methods=["POST"], strict_slashes=False)
def main():
    data = request.json
    logger.info(f"AUX: data from webhook/sells: {data}")

    if 'topic' in data:
        if data.get('topic') == 'orders_v2':
            order_id = data.get('resource').split("/")[2]
            if order_id not in orders:
                orders.append(order_id)
                thread = threading.Thread(target=run_process, args=(order_id, 'mercadolibre'))
                thread.start()
                return jsonify({"status": "accepted", "message": "Meli Selling Event"}), 202
            else:
                return jsonify({"status": "ignores", "message": "message wasnt a sell"}), 200
        else: 
            return jsonify({"status": "ignores", "message": "message wasnt a sell"}), 200

    elif 'store_id' in data:
        order_id = data.get('id')
        if order_id not in orders:
            orders.append(order_id)
            thread = threading.Thread(target=run_process, args=(order_id, 'tienda_nube'))
            thread.start()
            return jsonify({"status": "accepted", "message": "TiendaNube Selling Event"}), 202
        else:
            return jsonify({"status": "ignores", "message": "message wasnt a sell"}), 200
    else:
        return jsonify({"status": "ignores", "message": "message wasnt a sell"}), 200
    
