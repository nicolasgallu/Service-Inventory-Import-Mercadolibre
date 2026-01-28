import requests
from app.utils.logger import logger
from app.settings.config import DS_API_KEY, PROMPT_SYS_DESCR, PROMPT_SYS_BRAND

def completing_fields(product_name):
    """Returns {'description':description, 'brand':brand}"""

    logger.info("Using AI to complete Description & Brand")

    prompt_usr_description = f"el nombre del producto del cual necesito la descripcion es este: {product_name}"
    prompt_usr_brand = f"el nombre del producto del cual necesito la marca es este: {product_name}"

    prompts = {"description":{
                    "sys":PROMPT_SYS_DESCR,
                    "usr":prompt_usr_description},
               "brand":{
                    "sys":PROMPT_SYS_BRAND,
                    "usr":prompt_usr_brand}}

    headers = {
        "Authorization": f"Bearer {DS_API_KEY}",
        "Content-Type": "application/json"
    }

    for prompt in prompts:
        logger.info(f"Completing {prompt}")
        payload = {
            "model": "deepseek-chat",
            "messages": [
                    {"role": "system", "content": prompts[prompt]['sys']},
                    {"role": "user", "content":prompts[prompt]['usr']}
                ],
            "max_tokens": 500,
            "temperature": 0.55
        }       
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
        prompts[prompt]['result'] = response.json()['choices'][0]['message']['content']

    description = prompts['description']['result']
    brand = prompts['brand']['result']
    item_metadata = {'description':description,'brand':brand}
    return item_metadata