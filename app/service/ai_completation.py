import requests
import json
from app.utils.logger import logger
from app.service.database import load_ai_response, get_ai_prompt
from app.settings.config import DS_API_KEY


def aux_ai(sys_prompt, user_prompt, target_field):
    
    payload = {
        "model": "deepseek-chat",
        "messages": [
                {"role": "system", "content": json.dumps(sys_prompt)},
                {"role": "user", "content": json.dumps(user_prompt)}
            ],
        "max_tokens": 1000,
        "temperature": 0.55
    }       
    headers = {
        "Authorization": f"Bearer {DS_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post("https://api.deepseek.com/v1/chat/completions", 
                             headers=headers, 
                             json=payload
    )
    ai_response = {'ai_response' : response.json()['choices'][0]['message']['content']}
    logger.info(f"AI Generated response for field: {target_field}")
    return ai_response


def ai_call_prepublish(event_data, item_data):
    """generates description/title and if is not already made the brand."""
    
    item_id = item_data.get('id')
    original_title = item_data.get('product_name')
    brand = item_data.get('brand')
    model = item_data.get('model')
    
    target_field = event_data.get('data').get('field')
    user_prompt = event_data.get('data').get('prompt')

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


    ai_response = aux_ai(sys_prompt, user_prompt, target_field)
    load_ai_response(item_id, target_field, ai_response)

    if not brand:
        logger.info("AI Automatic - Creating Brand.")
        sys_prompt = get_ai_prompt('ai_generate_brand')
        user_prompt = {
            "original_name": original_title}
        ai_response = aux_ai(sys_prompt, user_prompt, 'brand')
        load_ai_response(item_id, 'brand', ai_response)

    if not model:
        logger.info("AI Automatic - Creating Model.")
        sys_prompt = get_ai_prompt('ai_generate_model')
        user_prompt = {
            "original_name": original_title}
        ai_response = aux_ai(sys_prompt, user_prompt, 'model')
        load_ai_response(item_id, 'model', ai_response)
