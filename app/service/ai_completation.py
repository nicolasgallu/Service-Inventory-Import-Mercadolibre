from app.utils.logger import logger
from app.service.llm_api import call_deepseek_api
from app.service.meli_api import get_data_for_meli
from app.service.database import update_method, get_method
from app.settings.config import SCHEMA_INVENTORY,SCHEMA_MERCADOLIBRE

PRODUCTS_TABLE = 'product_catalog_sync'
PROMPT_TABLE = 'prompts'

def _aux_get_ai_prompt():
    query = {
        'q_columns': [
            'ai_generate_title',
            'ai_generate_description',
            'ai_generate_brand',
            'ai_generate_model',
        ],
        'q_from':f'FROM {SCHEMA_MERCADOLIBRE}.{PROMPT_TABLE}',
        'q_limit':'LIMIT 1'
    }
    prompt = get_method(query)
    return prompt


def ai_call_prepublish(data, item_id):
    """generates description, title, brand and model."""
    
    item_data = get_data_for_meli(item_id)
    original_title = item_data.get('product_name')
    product_name_meli = item_data.get('product_name_meli')
    description = item_data.get('description')
    brand = item_data.get('brand')
    model = item_data.get('model')

    prompts = _aux_get_ai_prompt()
    data = {'id': {'value': item_id, 'type': 'char'}}

    if not product_name_meli:
        logger.info("AI Automatic - Creating Product Name Improved.")
        sys_prompt = prompts['ai_generate_title']
        user_prompt = {"original_name": original_title}
        ai_response = call_deepseek_api(sys_prompt, user_prompt)
        data['product_name_meli']={'value': ai_response, 'type': 'char'}
        logger.info("Done.")

    if not description:
        logger.info("AI Automatic - Creating Description.")
        sys_prompt = prompts['ai_generate_description']
        user_prompt = {"original_name": original_title}
        ai_response = call_deepseek_api(sys_prompt, user_prompt)
        data['description']={'value': ai_response, 'type': 'char'}
        logger.info("Done.")


    if not brand:
        logger.info("AI Automatic - Creating Brand.")
        sys_prompt = prompts['ai_generate_brand']
        user_prompt = {"original_name": original_title}
        ai_response = call_deepseek_api(sys_prompt, user_prompt)
        data['brand']={'value': ai_response, 'type': 'char'}
        logger.info("Done.")


    if not model:
        logger.info("AI Automatic - Creating Model.")
        sys_prompt = prompts['ai_generate_model']
        user_prompt = {"original_name": original_title}
        ai_response = call_deepseek_api(sys_prompt, user_prompt)
        data['model']={'value': ai_response, 'type': 'char'}
        logger.info("Done.")

    if len(data) >1:
        update_method(data, SCHEMA_INVENTORY, PRODUCTS_TABLE)

    else:
        logger.info("There is no Data to update on AI Prepublish Action")