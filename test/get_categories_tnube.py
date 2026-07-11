import json
import requests
from app.service.secrets import tienda_nube_secrets

ACCESS_TOKEN, STORE_ID = tienda_nube_secrets()

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "User-Agent": "MyApp (tu@email.com)",
    "Content-Type": "application/json",
}

response = requests.get(
    f"https://api.tiendanube.com/v1/{STORE_ID}/categories",
    headers=headers,
)

print("STATUS:", response.status_code)

response.raise_for_status()

categories = response.json()

result = []

for category in categories:
    result.append({
        "id": category["id"],
        "name": category["name"]["es"],
        "data": json.dumps(
            {
                "name": category["name"],
                "handle": category["handle"],
                "parent": category["parent"],
                "seo_title": category["seo_title"],
                "created_at": category["created_at"],
                "updated_at": category["updated_at"],
                "visibility": category["visibility"],
                "description": category["description"],
                "subcategories": category["subcategories"],
                "seo_description": category["seo_description"],
                "visibility_updated_at": category["visibility_updated_at"],
                "google_shopping_category": category["google_shopping_category"],
            },
            ensure_ascii=False,
        ),
    })

print(json.dumps(result, indent=4, ensure_ascii=False))