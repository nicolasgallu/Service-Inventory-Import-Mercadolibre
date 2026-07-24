import requests
import json
from app.utils.logger import logger
from app.service.notifications import enviar_mensaje_whapi
from app.settings.config import DS_API_KEY, TOKEN_WHAPI, PHONE_INTERNAL

def call_deepseek_api(sys_prompt, user_prompt):
    
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
    try:
        ai_response = response.json()['choices'][0]['message']['content']
        return ai_response
    
    except:
        response = response.json()
        logger.info(f"Failed to call DeepSeek AI.. {response}")
        enviar_mensaje_whapi(TOKEN_WHAPI, PHONE_INTERNAL, response)
        raise
    