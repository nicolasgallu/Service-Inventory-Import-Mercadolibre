
import requests
import json
from unidecode import unidecode
import logging
from datetime import datetime
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from app.service.database import update_method


def reconstruct_metadata_with_rules(item_ids, token):
    HEADER = {"Authorization": f"Bearer {token}"}
    INTERNAL_AVOID_REQMNT = ['BRAND', 'MODEL', 'GTIN', 'EMPTY_GTIN_REASON']
    results=[]
    default_settings = {
        "WARRANTY_TIME": "30 dias",
        "WARRANTY_TYPE": "Garantia del vendedor",
        "VALUE_ADDED_TAX": "21 %",
        "IMPORT_DUTY": "0 %",
        "MODE": "me2",
        "LOCAL_PICK_UP": "True",
        "FREE_SHIPPING": "False",
        "LISTING_TYPE": "gold_special",
        "LOGISTIC_TYPE": "drop_off",
    }

    for id in item_ids:

        item_id = item_ids[id]
        logger.info(f"--- Procesando {id} ---")
        logger.info(f"--- Procesando {item_id} ---")
        
        # 1. Obtener item para extraer category_id, price y atributos reales publicados
        item_resp = requests.get(f"https://api.mercadolibre.com/items/{item_id}", headers=HEADER)
        if item_resp.status_code != 200:
            logger.error(f"Error obteniendo {item_id}: {item_resp.text}")
            continue
            
        item_data = item_resp.json()
        category_id = item_data.get('category_id')
        price = item_data.get('price')
        
        # Diccionario rápido de atributos ya cargados {ID_ATRIBUTO: VALOR_PUBLICADO}
        published_attrs = {attr['id']: attr.get('value_name', '') for attr in item_data.get('attributes', [])}
        
        settings_list = [{'attributes':[]}, {'shipping':[]}, {'sale_terms':[]}, {'listing':[]}]
        
        for idx, setting_dict in enumerate(settings_list):
            for setting in setting_dict:
                logger.info(f"Building {setting} metadata para {category_id}..")
                response_data = []
                
                # 2. Consultas a la API o armado de reglas según la sección
                if setting == 'attributes':
                    response_data = requests.get(f"https://api.mercadolibre.com/categories/{category_id}/{setting}", headers=HEADER).json()
                
                elif setting == 'sale_terms':
                    response_data = requests.get(f"https://api.mercadolibre.com/categories/{category_id}/{setting}", headers=HEADER).json()
                    
                elif setting == 'shipping':
                    url = f"https://api.mercadolibre.com/categories/{category_id}/shipping_preferences"
                    res = requests.get(url, headers=HEADER).json()
                    logistics_modes = [log.get('mode') for log in res.get('logistics', [])]
                    
                    var1 = {'id': 'MODE', 'name': 'Metodo de Envio', 'values': [{'name': logistics_modes}], 'value_type': 'list', 'value_max_length': '255'}
                    var2 = {'id': 'LOCAL_PICK_UP', 'name': 'Buscar en Local', 'values': [{'name': ['True','False']}], 'value_type': 'list', 'value_max_length': '5'}
                    var3 = {'id': 'FREE_SHIPPING', 'name': 'Envio Gratis', 'values': [{'name': ['True','False']}], 'value_type': 'list', 'value_max_length': '5'}
                    var4 = {'id': 'LOGISTIC_TYPE', 'name': 'Tipo de Logistica', 'values': [{'name': ['fulfillment','cross_docking','self_service','drop_off','custom']}], 'value_type': 'list', 'value_max_length': '20'}
                    response_data = [var1, var2, var3, var4]
                    
                elif setting == 'listing':
                    res = requests.get(f"https://api.mercadolibre.com/sites/MLA/listing_prices?price={price}&category_id={category_id}", headers=HEADER).json()
                    listing_data = [{
                        "id": data.get('listing_type_id'),
                        "name": data.get('listing_type_name'),
                        "sale_fee_amount": data.get('sale_fee_amount'),
                        "sale_fee_details": data.get('sale_fee_details'),
                        "listing_fee_amount": data.get('listing_fee_amount'),
                        "listing_fee_details": data.get('listing_fee_details'),
                    } for data in res]
                    
                    response_data = [{
                        'id': 'LISTING_TYPE', 'name': 'Campaña de Cuotas', 'values': [{'name': listing_data}], 'value_type': 'list', 'value_max_length': '255'
                    }]

                # 3. Filtrar y armar el diccionario final
                for i in response_data:
                    if not isinstance(i, dict): continue
                    
                    field_id = i.get('id')
                    include = False
                    
                    if setting == 'attributes':
                        tags = i.get('tags', {})
                        bool_att_req = tags.get('required', False) or tags.get('conditional_required', False)
                        
                        # LA CORRECCIÓN ESTÁ ACÁ: Incluye si es obligatorio O si ya lo tenías publicado
                        if (bool_att_req or field_id in published_attrs) and field_id not in INTERNAL_AVOID_REQMNT:
                            include = True
                            
                    elif setting == 'sale_terms' and field_id in ['WARRANTY_TYPE', 'WARRANTY_TIME']:
                        include = True
                    elif setting in ['listing', 'shipping']:
                        include = True

                    if include:
                        val_examples = [val.get('name') for val in i.get('values', [])] if i.get('values') else ''
                        val_type = i.get('value_type', '')
                        
                        # Extraer el valor cargado o usar el default
                        if setting == 'attributes':
                            user_input = published_attrs.get(field_id, default_settings.get(field_id, ''))
                        else:
                            user_input = default_settings.get(field_id, '')

                        values = {
                            'id': field_id,
                            'name': i.get('name'),
                            'value_examples': val_examples,
                            'value_max_lenght': i.get('value_max_length', ''), 
                            'value_type': val_type,
                            'condition': 'Restricted Input' if str(val_type).lower() == 'list' else 'Free Input',
                            'user_input_value': user_input
                        }
                        settings_list[idx][setting].append(values)

        # 4. Formatear y preparar para el print final
        settings_str = unidecode(json.dumps(settings_list, ensure_ascii=False).replace("'", "").replace("\\n", ""))
        

        final_json = {
        "item_id": {
            "value": id,
            "type": "char"
        },
        "settings": {
            "value": settings_str,
            "type": "json"
        },
        "updated_at": {
            "value": datetime.now().isoformat(),
            "type": "datetime"
        }}

        results.append(final_json)

    with open("output.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, ensure_ascii=False)

#list_ids=None
#token = ""
#reconstruct_metadata_with_rules(list_ids, token)


import json
results=[]
with open("output.json", "r", encoding="utf-8") as f:
    data = json.load(f)

while data:
    item = data[0]  # siempre procesa el primero

    try:
        print(f"Processing item {item['item_id']['value']}...")

        update_method(item, "mercadolibre", "attributes")

        # Si llegó hasta acá, el UPDATE fue exitoso
        data.pop(0)

        # Persistir el progreso
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        print("OK")

    except Exception as e:
        print(f"ERROR: {e}")
        results.append(data)
        data.pop(0)
        continue

print("Finished.")