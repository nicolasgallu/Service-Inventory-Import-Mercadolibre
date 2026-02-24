from app.utils.logger import logger
from flask import Blueprint, request, Response, jsonify
from app.service.pipe_selling import pipeline_selling
import threading

# BLUEPRINT CREATION
meli_sell = Blueprint("wh_sell", __name__, url_prefix="/webhooks/sells")
@meli_sell.route("", methods=["POST"], strict_slashes=False)
def main():
    data = request.json
    if data.get('topic') == 'orders_v2':
        order_id = data.get('resource').split("/")[3]
        # 1. Creamos y lanzamos el hilo con la lógica pesada
        # Pasamos una copia de los datos para evitar problemas de contexto
        thread = threading.Thread(target=pipeline_selling, args=(order_id,))
        thread.start()
        # 2. Respondemos de inmediato
        # 202 significa "Accepted" (aceptado para procesamiento, pero no completado aún)
        return jsonify({"status": "accepted", "message": "Task dispatched to background"}), 202
    
