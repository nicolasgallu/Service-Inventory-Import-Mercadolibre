import asyncio
from app.utils.logger import logger
from app.service.llm_api import call_deepseek_api
from app.service.meli_api import get_data_for_meli
from app.service.database import update_method, get_method
from app.settings.config import SCHEMA_INVENTORY, SCHEMA_MERCADOLIBRE

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
        'q_from': f'FROM {SCHEMA_MERCADOLIBRE}.{PROMPT_TABLE}',
        'q_limit': 'LIMIT 1'
    }
    prompt = get_method(query)
    return prompt[0]


async def _call_ai(sys_prompt, user_prompt):
    return await asyncio.to_thread(
        call_deepseek_api,
        sys_prompt,
        user_prompt
    )


async def ai_call_prepublish(user_prompt, item_id):
    """generates description, title, brand and model."""

    item_data = get_data_for_meli(item_id)
    original_title = item_data.get('product_name')
    product_name_meli = item_data.get('product_name_meli')
    description = item_data.get('description')
    brand = item_data.get('brand')
    model = item_data.get('model')

    prompts = _aux_get_ai_prompt()
    data = {'id': {'value': item_id, 'type': 'char'}}

    if user_prompt:
        if user_prompt.get('prompt') and user_prompt.get('field'):
            logger.info("Received a user prompt action")
            prompt = user_prompt.get('prompt')
            column = None

            if not prompt:
                return

            if user_prompt.get('field') == 'product_name_meli':
                currentvalue = product_name_meli or original_title
                column = 'product_name_meli'
            else:
                currentvalue = description
                column = 'description'

            sys_prompt = f"""corregi este dato que te voy a dar segun mi prompt.
            (OBLIGATORIO: devolve solo el resultado mejorado, sin comments ni nada extra).
            dato a corregir: {currentvalue}"""

            ai_response = await _call_ai(sys_prompt, prompt)

            data[column] = {
                'value': ai_response,
                'type': 'char'
            }

            update_method(data, SCHEMA_INVENTORY, PRODUCTS_TABLE)
            return

    tasks = []

    if not product_name_meli or product_name_meli == '':
        logger.info("AI Automatic - Creating Product Name Improved.")
        sys_prompt = prompts['ai_generate_title']
        ai_user_prompt = {"original_name": original_title}
        tasks.append(_call_ai(sys_prompt, ai_user_prompt))
    else:
        tasks.append(None)

    if not description or description == '':
        logger.info("AI Automatic - Creating Description.")
        sys_prompt = prompts['ai_generate_description']
        ai_user_prompt = {"original_name": original_title}
        tasks.append(_call_ai(sys_prompt, ai_user_prompt))
    else:
        tasks.append(None)

    if not brand or brand == '':
        logger.info("AI Automatic - Creating Brand.")
        sys_prompt = prompts['ai_generate_brand']
        ai_user_prompt = {"original_name": original_title}
        tasks.append(_call_ai(sys_prompt, ai_user_prompt))
    else:
        tasks.append(None)

    if not model or model == '':
        logger.info("AI Automatic - Creating Model.")
        sys_prompt = prompts['ai_generate_model']
        ai_user_prompt = {"original_name": original_title}
        tasks.append(_call_ai(sys_prompt, ai_user_prompt))
    else:
        tasks.append(None)

    results = await asyncio.gather(*[ task if task is not None else asyncio.sleep(0, result=None) for task in tasks])
    product_name_response, description_response, brand_response, model_response = results

    if product_name_response is not None:
        data['product_name_meli'] = {'value': product_name_response,'type': 'char'}
        logger.info("Done Product Name.")

    if description_response is not None:
        data['description'] = {'value': description_response,'type': 'char'}
        logger.info("Done Description.")

    if brand_response is not None:
        data['brand'] = {'value': brand_response,'type': 'char'}
        logger.info("Done Brand.")

    if model_response is not None:
        data['model'] = {'value': model_response,'type': 'char'}
        logger.info("Done Model.")

    if len(data) > 1:
        update_method(data, SCHEMA_INVENTORY, PRODUCTS_TABLE)

    else:
        logger.info("There is no Data to update on AI Prepublish Action")
