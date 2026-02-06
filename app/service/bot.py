import requests
from app.settings.config import DS_API_KEY


def call_ai(user_prompt, ai_prompt):


    headers = {
        "Authorization": f"Bearer {DS_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
                {"role": "system", "content": ai_prompt},
                {"role": "user", "content": user_prompt}
            ],
        "max_tokens": 2000,
        "temperature": 0.45
    }       
    response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
    response = response.json()['choices'][0]['message']['content']
    return response
