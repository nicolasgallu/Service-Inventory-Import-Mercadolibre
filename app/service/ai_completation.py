from app.utils.logger import logger
from app.service.llm_api import call_deepseek_api
from app.service.meli_api import get_data_for_meli
from app.service.database import update_method, get_ai_prompt
from app.settings.config import SCHEMA_INVENTORY

PRODUCTS_TABLE = 'product_catalog_sync'

def ai_call_prepublish(data, item_id):
    """generates description, title, brand and model."""
    
    item_data = get_data_for_meli(item_id)
    original_title = item_data.get('product_name')
    product_name_meli = item_data.get('product_name_meli')
    description = item_data.get('description')
    brand = item_data.get('brand')
    model = item_data.get('model')

    if not product_name_meli:
        logger.info("AI Automatic - Creating Product Name Improved.")
        sys_prompt = get_ai_prompt('ai_generate_name')
        user_prompt = {
            "original_name": original_title}
        ai_response = call_deepseek_api(sys_prompt, user_prompt)
        data = {
            'id': {
                'value': item_id, 
                'type': 'char'
            },
            'product_name_meli': {
                'value': ai_response, 
                'type': 'char'
            }
        }
        update_method(data, SCHEMA_INVENTORY, PRODUCTS_TABLE)


    if not description:
        logger.info("AI Automatic - Creating Description.")
        sys_prompt = get_ai_prompt('ai_generate_description')
        user_prompt = {
            "original_name": original_title}
        ai_response = call_deepseek_api(sys_prompt, user_prompt)
        data = {
            'id': {
                'value': item_id, 
                'type': 'char'
            },
            'description': {
                'value': ai_response, 
                'type': 'char'
            }
        }
        update_method(data, SCHEMA_INVENTORY, PRODUCTS_TABLE)


    if not brand:
        logger.info("AI Automatic - Creating Brand.")
        sys_prompt = get_ai_prompt('ai_generate_brand')
        user_prompt = {
            "original_name": original_title}
        ai_response = call_deepseek_api(sys_prompt, user_prompt)
        data = {
            'id': {
                'value': item_id, 
                'type': 'char'
            },
            'brand': {
                'value': ai_response, 
                'type': 'char'
            }
        }
        update_method(data, SCHEMA_INVENTORY, PRODUCTS_TABLE)

    if not model:
        logger.info("AI Automatic - Creating Model.")
        sys_prompt = get_ai_prompt('ai_generate_model')
        user_prompt = {
            "original_name": original_title}
        ai_response = call_deepseek_api(sys_prompt, user_prompt)
        data = {
            'id': {
                'value': item_id, 
                'type': 'char'
            },
            'model': {
                'value': ai_response, 
                'type': 'char'
            }
        }
        update_method(data, SCHEMA_INVENTORY, PRODUCTS_TABLE)

    else:
        logger.info("AI Autocompletation already done.")


