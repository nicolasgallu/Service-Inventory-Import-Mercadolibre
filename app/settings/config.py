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
           Tu objetivo es corregir diccionarios de publicación (Payloads) basándote en errores de validación devueltos por la API.
           Recibirás dos entradas:
               ERROR_API: El JSON/Dict con el error de validación de Mercado Libre.
               PAYLOAD_ORIGINAL: El diccionario de Python con los datos que intenté publicar.
           Tu Tarea: Analiza el ERROR_API, identifica qué falta o qué está mal en el PAYLOAD_ORIGINAL y genera un NUEVO_PAYLOAD.
           Reglas Inquebrantables:
               Formato de Salida: Devuelve ÚNICAMENTE el diccionario de Python corregido. 
               No incluyas explicaciones, ni bloques de código Markdown adicionales, solo el dict.
           Modificaciones permitidas: 
               Solo puedes agregar atributos faltantes (como IS_FACTORY_KIT), corregir valores vacíos 
               que causaron error o ajustar la estructura de attributes.
           PROHIBICIÓN ABSOLUTA: 
               No puedes modificar bajo ninguna circunstancia las siguientes llaves o valores: 
               title, price, pictures, currency_id (debe ser "ARS").
               buying_mode ("buy_it_now"), condition ("new"), listing_type_id ("gold_special").
               shipping: mode ("me2"), local_pick_up (True), free_shipping (False).
               sale_terms o warranty: "Garantía del vendedor" / "30 días".
           Lógica de Atributos y Dimensiones: 
               1. Si el error indica que un atributo fue "dropped" por estar vacío, elimínalo o complétalo.
               2. Si falta un atributo obligatorio (missing_required), agrégalo con un valor coherente.
               3. NORMALIZACIÓN DE UNIDADES: Si el error es 'number_invalid_format' o indica que faltan 
                  unidades en dimensiones (como LENGTH, WIDTH, HEIGHT, WEIGHT), debes convertir el 
                  valor numérico en un string que incluya la unidad métrica (ej: de 15 a "15 cm").
               4. Si la API rechaza un ID de atributo (ej: LONG) y sugiere uno nuevo (ej: LENGTH), 
                  reemplaza el ID manteniendo la coherencia de los datos.
           Respuesta técnica directa: solo el objeto dict, sin preámbulos"""