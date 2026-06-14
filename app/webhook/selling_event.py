from app.utils.logger import logger
from flask import Blueprint, request, jsonify
from app.service.pipe_selling import pipeline_selling
import threading

memory = set()
memory_lock = threading.Lock()

def run_pipe_selling(order_id, platform):
    pipeline_selling(order_id, platform)
    with memory_lock:
        logger.info(f"Removing from memory: {order_id}")
        memory.remove(order_id)

meli_sell = Blueprint("wh_sell", __name__, url_prefix="/webhooks/sells")
@meli_sell.route("", methods=["POST"], strict_slashes=False)
def main():
    data = request.json

    if 'topic' in data and data.get('topic') == 'orders_v2':
        data = {
            'platform': 'mercadolibre',
            'order_id': data.get('resource').split("/")[2]
        }
    elif 'store_id' in data:
        data = {
            'platform': 'tienda_nube',
            'order_id': data.get('id')
        }
    else:
        logger.info("Sell Webhook: Event Rejected [not a sell]")
        return jsonify({"status": "ignores", "message": "event rejected"}), 200

    order_id = data.get('order_id')
    platform = data.get('platform')
    if order_id not in memory:
        memory.add(order_id)
        thread = threading.Thread(target=run_pipe_selling, args=(order_id, platform))
        thread.start()
        logger.info("Sell Webhook: Event Accepted [new order]")
        return jsonify({"status": "accepted", "message": "event received"}), 200
    else:
        logger.info("Sell Webhook: Event Rejected [already in pipeline]")
        return jsonify({"status": "ignores", "message": "event rejected"}), 200