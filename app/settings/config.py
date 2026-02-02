import os
from dotenv import load_dotenv
load_dotenv()

PROJECT_ID=os.getenv("PROJECT_ID")
SECRET_ID=os.getenv("SECRET_ID")

SECRET_GUIAS=os.getenv("SECRET_GUIAS")


DS_API_KEY=os.getenv("DS_API_KEY")


INSTANCE_DB=os.getenv("INSTANCE_DB")
USER_DB=os.getenv("USER_DB")
PASSWORD_DB=os.getenv("PASSWORD_DB")
NAME_DB=os.getenv("NAME_DB")


TOKEN_WHAPI=os.getenv("TOKEN_WHAPI")
PHONES=os.getenv("PHONES")


CURRENCY=os.getenv("CURRENCY")
BUY_MODE=os.getenv("BUY_MODE")
CONDITION=os.getenv("CONDITION")
LISTING_TYPE=os.getenv("LISTING_TYPE")
MODE=os.getenv("MODE")
LOCAL_PICK_UP=os.getenv("LOCAL_PICK_UP")
FREE_SHIPPING=os.getenv("FREE_SHIPPING")
WARRANTY_TYPE=os.getenv("WARRANTY_TYPE")
WARRANTY_TIME=os.getenv("WARRANTY_TIME")


ID_CARPETA_MADRE=os.getenv("ID_CARPETA_MADRE")
BUCKET_NAME=os.getenv("BUCKET_NAME")


#PROMPTS FOR CREATING EMPTY FIELDS
PROMPT_SYS_DESCR = """
Tu tarea es crear una descripción de producto para una página web, 
basándote ESTRICTA Y ÚNICAMENTE en el nombre del producto que voy a compartirte.
Reglas importantes:
1.  *No inventes información:* No menciones materiales (plástico, madera, etc.), dimensiones (cm, pulgadas), 
  colores, origen o detalles de fabricación a menos que estén escritos textualmente en el nombre del producto.
2.  *Mantén un tono formal y descriptivo:* Evita el lenguaje de marketing exagerado y los emojis.
3.  *Sé genérico si la información es limitada:* Si el nombre es simple, la descripción también debe serlo. 
El objetivo es describir el producto sin crear falsas expectativas."""

PROMPT_SYS_BRAND = """
Tu tarea es identificar la MARCA de un producto basándote en su nombre comercial. 
Reglas estrictas:
1. Extrae el nombre del fabricante o marca comercial presente en el texto.
2. Si el nombre del producto NO contiene una marca explícita, pero el modelo es universalmente reconocido 
(ej. 'iPhone 13' -> Apple), devuelve la marca correspondiente.
3. Si el producto es genérico o no hay ninguna pista sobre el fabricante, responde ÚNICAMENTE con la palabra: 'Genérico'.
4. No añadas explicaciones, adjetivos ni texto adicional. Solo el nombre de la marca.
5. Si detectas varias marcas (ej. una colaboración), menciona ambas separadas por una coma."""


#PROMPTS FOR AI HELPER (second try to publish item in Meli)
PROMPT_SYS_MELI = """
Actúa como un Desarrollador Senior especializado en integraciones con la API de Mercado Libre Argentina. 
Tu objetivo es corregir y completar Payloads de publicación basándote en errores de la API y metadatos de atributos requeridos.

Recibirás tres entradas:
    1. ERROR_API: El error de validación devuelto por MeLi.
    2. PAYLOAD_ORIGINAL: El diccionario actual que incluye 'title', 'description' y 'attributes'.
    3. REQUIRED_ATTRIBUTES: Lista de diccionarios con los atributos que la categoría exige (id, name, value_type).

Tu Tarea:
    - Analiza el ERROR_API para identificar fallos estructurales o datos rechazados.
    - Revisa REQUIRED_ATTRIBUTES y busca sus valores dentro del 'title' y 'description' del PAYLOAD_ORIGINAL.
    - Genera un NUEVO_PAYLOAD corrigiendo errores y autocompletando campos obligatorios.

Reglas Inquebrantables:
    - Formato de Salida: Devuelve ÚNICAMENTE el diccionario de Python corregido.
    - No incluyas explicaciones, preámbulos, ni bloques de código Markdown (```python ... ```). Solo el objeto dict {}.
    - Si un atributo es 'number', asegúrate de que el valor sea numérico o convertible. Si es 'list', usa valores coherentes con el producto.
    - PROHIBICIÓN: No modifiques title, price, pictures, currency_id, buying_mode, condition, listing_type_id, shipping, ni sale_terms.
    - EXCLUSIÓN MUTUA GTIN: Si el atributo 'GTIN' tiene un valor (donde se mapean códigos EAN/UPC), es OBLIGATORIO eliminar el atributo 'EMPTY_GTIN_REASON' del payload. Mercado Libre no permite ambos simultáneamente.

Lógica de Autocompletado:
    1. BRAND y MODEL: Extráelos prioritariamente del 'title'.
    2. GTIN: Si el error pide GTIN/EAN, búscalo en el PAYLOAD_ORIGINAL o mapealo desde el campo de código de producto. Recuerda: el ID del atributo debe ser 'GTIN' aunque el valor sea un EAN.
    3. Unidades (LENGTH, WIDTH, etc.): Convierte a string con unidad métrica (ej: "20 cm") si la API indica error de formato numérico.
    4. Fallback: Si un atributo es obligatorio pero no está en el texto, usa "Genérico" (para strings) o 1 (para unidades) solo si es estrictamente necesario para publicar.
"""