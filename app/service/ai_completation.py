from app.utils.logger import logger
from app.service.llm_api import call_deepseek_api
from app.service.database import update_method, get_ai_prompt

schema = 'app_import'
table = 'product_catalog_sync'


def ai_call_prepublish(data, item_data):
    """generates description/title and if is not already made the brand."""
    
    item_id = item_data.get('id')
    original_title = item_data.get('product_name')
    brand = item_data.get('brand')
    model = item_data.get('model')

    if data:
        target_field = data.get('field', None)
        user_prompt = data.get('prompt', None)
        logger.info(f"Request to create information with AI over field: {target_field}.")
        if target_field == "product_name_meli":
            previous_title = item_data.get('product_name_meli')
            sys_prompt = get_ai_prompt('ai_generate_title')
            user_prompt = {
                "original_name": original_title,
                "previous_name_option": previous_title,
                "prompt":user_prompt}
        elif target_field == "description":
            previous_description = item_data.get('description')
            dimentions = item_data.get('dimentions')
            sys_prompt = get_ai_prompt('ai_generate_description')
            user_prompt = {
                "original_name": original_title,
                "dimentions":dimentions,
                "previous_description_option": previous_description,
                "prompt":user_prompt}
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
        update_method(data, schema ,table)

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
        update_method(data, schema ,table)

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
        update_method(data, schema ,table)

    else:
        logger.info("AI Autocompletation already done.")


