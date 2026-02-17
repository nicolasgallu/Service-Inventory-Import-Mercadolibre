import threading
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
    logger.info("Receving notification from App Import - Dispatching thread")
    # 1. Creamos y lanzamos el hilo con la lógica pesada
    # Pasamos una copia de los datos para evitar problemas de contexto
    thread = threading.Thread(target=pipeline_publish, args=(response,))
    thread.start()
    # 2. Respondemos de inmediato
    # 202 significa "Accepted" (aceptado para procesamiento, pero no completado aún)
    return jsonify({"status": "accepted", "message": "Task dispatched to background"}), 202