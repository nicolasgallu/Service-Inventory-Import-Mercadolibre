from app.service.secrets import meli_secrets
from app.service.database import get_item_data, load_item_metadata, load_meli_id
from app.service.ai_metadata import completing_fields
from app.service.meli_api import publish, pause_item
from app.utils.logger import logger
from app.settings.config import SECRET_GUIAS
from flask import Blueprint, request, Response, jsonify

# BLUEPRINT CREATION
meli_publish = Blueprint("wh_publish", __name__, url_prefix="/webhooks/goog-app/publications")
@meli_publish.route("", methods=["POST"], strict_slashes=False)
def main():
    
    response = request.json
    
    try:
        if SECRET_GUIAS == response['secret']: #!!CHANGE FOR SECRET.
            logger.info("Receving notification from App Import")
            
            #Getting ItemID and EventType
            item_id = response['item_id']
            event_type = response['event_type']
            logger.info(f"Event Received: {event_type}")

            if event_type in ["publish","paused"]:

                #Getting Item metadata and casting price
                item_data = get_item_data(item_id)
                product_name = item_data['product_name']
                meli_id = item_data['meli_id']
                item_data['price'] = float(item_data['price'])

                #Getting Meli Credentials
                token = meli_secrets()

                if event_type == "publish":
                    #only when these fields are empty we run the AI Search.
                    if item_data['description'] is None or item_data['brand'] is None:
                        item_metadata = completing_fields(product_name)
                        load_item_metadata(item_id, item_metadata)
                        item_data['description'] = item_metadata['description']
                        item_data['brand'] =  item_metadata['brand']

                    #publish or updating item at mercadolibre
                    meli_id = publish(item_data, meli_id, token)

                    #writting meli id in our DB and returning HTTP
                    if meli_id is not None:
                        load_meli_id(item_id, meli_id)
                    return Response(status=200)

                if event_type == "paused":
                    pause_item(meli_id, token)
                    return Response(status=200)

            else:
                return Response(status=400)
        
        else:
            return Response(status=401)
        
    
    except Exception as error:
        return jsonify({"error": str(error)}), 500