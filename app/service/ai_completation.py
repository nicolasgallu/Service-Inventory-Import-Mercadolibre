from app.utils.logger import logger
from app.service.llm_api import call_deepseek_api
from app.service.meli_api import get_data_for_meli
from app.service.database import update_method, get_ai_prompt
from app.settings.config import SCHEMA_INVENTORY

PRODUCTS_TABLE = 'product_catalog_sync'

def ai_call_prepublish(data, item_id):
    """generates description/title and if is not already made the brand."""
    
    item_data = get_data_for_meli(item_id)
    original_title = item_data.get('product_name')
    brand = item_data.get('brand')
    model = item_data.get('model')

    target_fields = []
    prompts = []
    if data:
        target_fields.append(data.get('field'))
        prompts.append(data.get('prompt'))
    else:
        target_fields = ['product_name_meli','description']
        prompts = ["modifica este titulo, que sea mas comercial para Mercadolibre y contenga menos de 60 caracteres.",
            "genera una descripcion corta y comercial para Mercadolibre"]
        
    for i,target_field in enumerate(target_fields):
        logger.info(f"Request to create information with AI over field: {target_field}.")
        if target_field == "product_name_meli":
            previous_title = item_data.get('product_name_meli')
            sys_prompt = get_ai_prompt('ai_generate_title')
            user_prompt = {
                "original_name": original_title,
                "previous_name_option": previous_title,
                "prompt":prompts[i]}
        elif target_field == "description":
            previous_description = item_data.get('description')
            dimentions = item_data.get('dimentions')
            sys_prompt = get_ai_prompt('ai_generate_description')
            user_prompt = {
                "original_name": original_title,
                "dimentions":dimentions,
                "previous_description_option": previous_description,
                "prompt":prompts[i]}
            
        ai_response = call_deepseek_api(sys_prompt, user_prompt)
        data = {
            'id': {
                'value': item_id, 
                'type': 'char'
            },
            target_field: {
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


