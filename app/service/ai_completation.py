import requests
from app.utils.logger import logger
from app.service.database import load_item_metadata
from app.settings.config import DS_API_KEY, PROMPT_SYS_DESCR, PROMPT_SYS_BRAND


def completing_fields(item_data):
    """In case Brand or Description are empty we complete them using AI"""
    
    prompts=[]
    item_id = item_data['id']
    description = item_data['description']
    brand = item_data['brand']
    product_name = item_data['product_name']

    logger.info("Starting autocompletation fields..")

    if description is None:
        logger.info("Description needed to Autocomplete.")
        prompt_usr_description = f"el nombre del producto del cual necesito la descripcion es este: {product_name}"
        prompts.append(
                    {"type":"description",
                    "sys":PROMPT_SYS_DESCR,
                    "usr":prompt_usr_description})


    if brand is None: 
        logger.info("Brand needed to Autocomplete.")
        prompt_usr_brand = f"el nombre del producto del cual necesito la marca es este: {product_name}"
        prompts.append(
                    {"type":"brand",
                    "sys":PROMPT_SYS_BRAND,
                    "usr":prompt_usr_brand})


    headers = {
        "Authorization": f"Bearer {DS_API_KEY}",
        "Content-Type": "application/json"
    }

    

    for prompt in prompts:
        logger.info(f"Autocompleting for: {prompt['type']}")
        payload = {
            "model": "deepseek-chat",
            "messages": [
                    {"role": "system", "content": prompt['sys']},
                    {"role": "user", "content":prompt['usr']}
                ],
            "max_tokens": 500,
            "temperature": 0.55
        }       
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
        if prompt['type'] == "description":
            description = response.json()['choices'][0]['message']['content']
        else:
            brand = response.json()['choices'][0]['message']['content']

    logger.info("Finishing autocompletation fields..")

    load_item_metadata(item_id, {'description':description, 'brand':brand})

    return brand ,description
