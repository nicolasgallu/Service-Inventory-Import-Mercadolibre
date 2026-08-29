import asyncio
from app.utils.logger import logger
from app.service.llm_api import call_deepseek_api
from app.integrations.mercadolibre.meli_api import get_data_for_meli
from app.settings.config import SCHEMA_INVENTORY, SCHEMA_AI, SCHEMA_MERCADOLIBRE
from app.db.helpers import get_one, execute
from sqlalchemy.exc import IntegrityError

PRODUCTS_TABLE = 'products'
PROMPTS_TABLE = 'prompts'
ATTRIBUTES_TABLE= 'attributes'
PRODUCT_LISTING_TABLE= 'product_listings'

#crear prompts table en un lugar centralizado.
#recordarfiltar por ecommerce_account_id ya que cada account tiene su criterio.

#AVISARLE A LEA QUE EL CONTRATO DEL PAYLOAD PARA PROMPTS CAMBIO.
#AHORA LOS CAMPOS SIGUEN VINIENDO EN DATA PERO EL NOMBRE DE MELI CAMBIO A name_edited.
#RESOLVER SI ES QUE ME MANDA MAL ALGO..

def _aux_get_ai_prompt():
    sql = (
        "SELECT "
        + "ai_generate_title, "
        + "ai_generate_description, "
        + "ai_generate_brand, "
        + "ai_generate_model "
        + "FROM " + SCHEMA_AI + "." + PROMPTS_TABLE
    )
    row = get_one(sql)
    return row


def _update_products(product_id, data):
    fields = []
    params = {"id": product_id}
    for field, value in data.items():
        if value is not None:
            fields.append(f"{field} = :{field}")
            params[field] = value
    if not fields:
        return
    
    sql = (
        "UPDATE " + SCHEMA_INVENTORY + "." + PRODUCTS_TABLE
        + " SET " + ", ".join(fields)
        + " WHERE id = :id"
    )
    execute(sql, params)


def _insert_product_listing(product_id, ecommerce_account_id):

    logger.info('running insert in listing table.')
    sql = (
        "INSERT INTO " + SCHEMA_MERCADOLIBRE + "." + PRODUCT_LISTING_TABLE
        + " (product_id, ecommerce_account_id)"
        + " VALUES (:product_id, :ecommerce_account_id)"
    )
    try:
        execute(sql, {'product_id': product_id, 'ecommerce_account_id': ecommerce_account_id})
        logger.info("New listing created.")
    except IntegrityError:
        logger.info("Not new listing created. (already created)")
        pass

def _insert_attributes(product_listing_id):

    logger.info('running insert in attributes.')
    sql = (
        "INSERT INTO " + SCHEMA_MERCADOLIBRE + "." + ATTRIBUTES_TABLE
        + " (product_listing_id)"
        + " VALUES (:product_listing_id)"
    )
    try:
        execute(sql, {"product_listing_id": product_listing_id,})
        logger.info("New Attribute created.")
    except IntegrityError:
        logger.info("Not new Attribute created. (already created)")
        pass



async def _call_ai(sys_prompt, user_prompt):
    return await asyncio.to_thread( call_deepseek_api, sys_prompt, user_prompt)


async def ai_call_prepublish(payload):
    """generates description, title, brand and model."""

    ##CHEQUEAR EL CONTRATO A ESTE NIVEL,
    ##SI EXISTE DATA PERO NO HAY PROMPT ROMPER.
    #if not prompt:return
    #user_prompt.get('prompt') and user_prompt.get('field'):

    product_id = payload.get('product_id')
    ecommerce_account_id = payload.get('ecommerce_account_id')
    user_prompt = payload.get('data')

    _insert_product_listing(product_id, ecommerce_account_id)
    prompts = _aux_get_ai_prompt()
    item_data = get_data_for_meli(product_id)
    
    name_original = item_data.get('name')
    name_edited = item_data.get('name_edited')
    description = item_data.get('description')
    brand = item_data.get('brand')
    model = item_data.get('model')
    product_listing_id = item_data.get('product_listing_id')
    
    if user_prompt:
        logger.info("Received a user prompt action")
        prompt = user_prompt.get('prompt')
        if user_prompt.get('field') == 'name_edited':
            currentvalue = name_edited or name_original
            column = 'name_edited'
        else:
            currentvalue = description
            column = 'description'

        sys_prompt = (
            "corregi este dato que te voy a dar segun mi prompt."
            +"(OBLIGATORIO: devolve solo el resultado mejorado, sin comments ni nada extra)."
            +"dato a corregir: " 
            + currentvalue
        )

        ai_response = await _call_ai(sys_prompt, prompt)
        data = {column: ai_response}
        _update_products(product_id, data)
        return


    tasks = []

    if not name_edited or name_edited == '':
        logger.info("AI Automatic - Creating Product Name Improved.")
        sys_prompt = prompts['ai_generate_title']
        ai_user_prompt = {"original_name": name_original}
        tasks.append(_call_ai(sys_prompt, ai_user_prompt))
    else:
        tasks.append(None)

    if not description or description == '':
        logger.info("AI Automatic - Creating Description.")
        sys_prompt = prompts['ai_generate_description']
        ai_user_prompt = {"original_name": name_original}
        tasks.append(_call_ai(sys_prompt, ai_user_prompt))
    else:
        tasks.append(None)

    if not brand or brand == '':
        logger.info("AI Automatic - Creating Brand.")
        sys_prompt = prompts['ai_generate_brand']
        ai_user_prompt = {"original_name": name_original}
        tasks.append(_call_ai(sys_prompt, ai_user_prompt))
    else:
        tasks.append(None)

    if not model or model == '':
        logger.info("AI Automatic - Creating Model.")
        sys_prompt = prompts['ai_generate_model']
        ai_user_prompt = {"original_name": name_original}
        tasks.append(_call_ai(sys_prompt, ai_user_prompt))
    else:
        tasks.append(None)

    results = await asyncio.gather(*[ task if task is not None else asyncio.sleep(0, result=None) for task in tasks])
    product_name_response, description_response, brand_response, model_response = results

    data = {
    "name_edited": product_name_response,
    "description": description_response,
    "brand": brand_response,
    "model": model_response,
    }

    _update_products(product_id, data)

    _insert_attributes(product_listing_id)