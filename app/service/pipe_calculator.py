from app.service.secrets import meli_secrets
from app.service.database import get_item_data, load_selling_calculation
from app.service.meli_api import get_category_id, get_selling_cost, get_shipping_cost
from app.utils.logger import logger

def calculating_cost(response):
    item_id= response['item_id']
    token:str= meli_secrets()
    logger.info(f"Procesing selling calculation for ID: {item_id}")
    user_id = token.split('-')[-1]
    item_data= get_item_data(item_id)
    category_id= get_category_id(item_data["product_name"], token)
    cost_detail= get_selling_cost(item_data, category_id, token)
    cost_detail_complete= get_shipping_cost(cost_detail, item_data, category_id, user_id, token)
    cost_detail_complete['item_id']= item_id
    cost_detail_complete['category_id']= category_id
    load_selling_calculation(cost_detail_complete)