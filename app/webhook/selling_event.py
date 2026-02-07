from app.utils.logger import logger
from flask import Blueprint, request, Response, jsonify
from app.service.secrets import meli_secrets
from app.service.database import insert_order
import requests

# BLUEPRINT CREATION
meli_sell = Blueprint("wh_sell", __name__, url_prefix="/webhooks/sells")
@meli_sell.route("", methods=["POST"], strict_slashes=False)

def main():
    data = request.json
    
    # 1. Filter only for sale notifications (orders_v2)
    if data.get('topic') == 'orders_v2':
        resource_path = data.get('resource') # Example: /orders/2000003508419012
        logger.info(f"New sale notification received: {resource_path}")
        
        # 2. Process sale information
        procesar_venta(resource_path)
        
        # ML expects a fast 200 OK to avoid retries
        return jsonify({"status": "received"}), 200
    
    # If other topics are received (questions, items), we return 200 but ignore them
    return jsonify({"status": "ignored"}), 200


def procesar_venta(resource_path):
    try:
        token = meli_secrets()
        url = f"https://api.mercadolibre.com{resource_path}"
        headers = {'Authorization': f'Bearer {token}'}
        
        # Request order details from MeLi API
        response = requests.get(url, headers=headers)
        order_data = response.json()
        
        # Extract unique Order ID and sale date
        order_id = order_data.get('id')
        created_at = order_data.get('date_created')
        
        # 3. Detect product and quantities (using loop cause there can be multiple differents items in one single purcharse)
        for item_info in order_data.get('order_items', []):
            meli_id = item_info.get('item', {}).get('id')
            quantity = item_info.get('quantity')
            
            logger.info("SALE DETECTED:")
            logger.info(f"Order ID: {order_id}")
            logger.info(f"Date: {created_at} ({meli_id})")
            logger.info(f"Units: {quantity}")

            order = {'id':order_id, 'meli_id':meli_id, 'units':quantity, 'created_at': created_at}

            insert_order(order)
            
    except Exception as e:
        logger.error(f"Error processing the order: {e}")

