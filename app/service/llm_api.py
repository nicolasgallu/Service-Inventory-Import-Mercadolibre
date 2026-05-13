import requests
import json
from app.settings.config import DS_API_KEY

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
    ai_response = response.json()['choices'][0]['message']['content']
    return ai_response