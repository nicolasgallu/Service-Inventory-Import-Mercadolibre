from app.service.secrets import meli_secrets
from app.service.meli_api import get_data_for_meli, _generate_category_options, calculate_cost
from app.utils.logger import logger

def calculating_cost(response):
    item_id = response['item_id']
    logger.info(f"Procesing selling calculation for ID: {item_id}")
    token:str = meli_secrets()
    user_id = token.split('-')[-1]

    item_data = get_data_for_meli(item_id)
    if item_data.get('category_options') == None:
        _generate_category_options(item_id, item_data.get('product_name'), token)

    calculate_cost(item_data, user_id, token)
