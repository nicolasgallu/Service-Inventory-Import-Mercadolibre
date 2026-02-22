import requests
from app.utils.logger import logger
from app.service.database import load_ai_response
from app.settings.config import DS_API_KEY


def ai_call_prepublish(event_data, item_data):
    """generates description/title and if is not already made the brand."""
    
    item_id = item_data.get('id')
    title = item_data.get('product_name')
    brand = item_data.get('brand')

    field = event_data.get('data').get('field')
    user_prompt = event_data.get('data').get('prompt')

    if field == 'product_name_meli':
        logger.info("the request is for creating the title")
        prev_data = item_data.get('product_name_meli')
        sys_prompt = f"""
            Tu tarea es crear un título optimizado para Mercado Libre basándote ESTRICTA Y ÚNICAMENTE en el nombre del producto proporcionado, genera
            un titulo atractivo ya que vas a recibir el nombre original y normalmente suele no ser tan llamativo para vender.
        
            **Contexto de la tarea:**
            1. Si no existe un título previo 'prev_data', genera el título desde cero siguiendo las reglas de optimización.
            2. Si ya existe un título previo 'prev_data', tu objetivo es aplicar el feedback del usuario para refinarlo, manteniendo la estructura de venta.
        
            **Reglas de optimización (Meli):**
            4. *Formato de salida:* Devuelve EXCLUSIVAMENTE el texto del título. No incluyas comillas, comentarios, etiquetas de markdown ni introducciones.
        
            **Datos:**
            - Nombre original del producto: {title}
            - prev_data (contexto para cambios): {prev_data}
            """
    else:
        logger.info("the request is for creating the description")
        prev_data = item_data.get('description')
        sys_prompt = f"""
            Tu tarea es crear una descripción de producto para una página web basándote ESTRICTA Y ÚNICAMENTE en el nombre proporcionado.
            **Contexto de la tarea:**
            1. Si no existe una descripción previa 'prev_data', genera el contenido desde cero siguiendo las reglas generales.
            2. Si ya existe una descripción previa 'prev_data', tu objetivo es actuar sobre el feedback del usuario para modificar y mejorar el resultado anterior, manteniendo siempre la coherencia con las reglas.

            **Reglas importantes:**
            1. *No inventes información:* No menciones materiales, dimensiones, colores u origen a menos que estén en el nombre del producto.
            2. *Tono formal y descriptivo:* Evita lenguaje de marketing exagerado y emojis.
            3. *Simplicidad:* Si el nombre es limitado, la descripción debe ser genérica y breve para no crear falsas expectativas.
            4. *Formato de salida:* Devuelve EXCLUSIVAMENTE el texto de la descripción. No incluyas comentarios, introducciones, etiquetas de markdown ni ningún otro contenido adicional.

            **Datos:**
            - Nombre del producto: {title}
            - prev_data (contexto para cambios): {prev_data}
            """


    logger.info(f"Autocompleting field: {field}")

    payload = {
        "model": "deepseek-chat",
        "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
        "max_tokens": 1000,
        "temperature": 0.55
    }       
    headers = {
        "Authorization": f"Bearer {DS_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
    ai_response = {'ai_response' : response.json()['choices'][0]['message']['content']}
    load_ai_response(item_id, field, ai_response)


    if brand:
        None
    else:
        logger.info("Autocompleting Brand")
        user_prompt = f"el nombre del producto del cual necesito la marca es este: {title}"
        sys_prompt = """
            Tu tarea es identificar la MARCA de un producto basándote en su nombre comercial. 
            Reglas estrictas:
            1. Extrae el nombre del fabricante o marca comercial presente en el texto.
            2. Si el nombre del producto NO contiene una marca explícita, pero el modelo es universalmente reconocido 
            (ej. 'iPhone 13' -> Apple), devuelve la marca correspondiente.
            3. Si el producto es genérico o no hay ninguna pista sobre el fabricante, responde ÚNICAMENTE con la palabra: 'Genérico'.
            4. No añadas explicaciones, adjetivos ni texto adicional. Solo el nombre de la marca.
            5. Si detectas varias marcas (ej. una colaboración), menciona ambas separadas por una coma."""
        payload = {
            "model": "deepseek-chat",
            "messages": [
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ],
            "max_tokens": 1000,
            "temperature": 0.55
        }       
        headers = {
            "Authorization": f"Bearer {DS_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.post("https://api.deepseek.com/v1/chat/completions", headers=headers, json=payload)
        ai_response = {'ai_response' : response.json()['choices'][0]['message']['content']}
        load_ai_response(item_id, 'brand', ai_response)



