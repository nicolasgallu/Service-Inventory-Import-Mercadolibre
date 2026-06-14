from app.service.pipe_publish import pipeline_publish
from app.utils.logger import logger
from app.settings.config import SECRET_GUIAS
from flask import Blueprint, request, jsonify
import threading

memory = set()
memory_lock = threading.Lock()

def run_pipe_publish(response):
    id = response.get('item_id')
    pipeline_publish(response)
    with memory_lock:
        logger.info(f"Removing from memory: {id}")
        memory.remove(id)

# BLUEPRINT CREATION
meli_publish = Blueprint("wh_publish", __name__, url_prefix="/webhooks/publications")
@meli_publish.route("", methods=["POST"], strict_slashes=False)
def main():
    response = request.json
    if SECRET_GUIAS != response['secret']:
        return jsonify({"status": "not accepted"}), 400
    
    id = response.get('item_id')
    logger.info(f"evento recibido para item: {id}")
    with memory_lock:
        if id in memory:
            logger.warning(f"Skipped event for item: {id}")
            return jsonify({"status": "skipping"}), 201
    
    logger.warning(f"Processing event for item: {id}")
    memory.add(id)
    thread = threading.Thread(target=run_pipe_publish, args=[response])
    thread.start()
    return jsonify({"status": "accepted"}), 200
