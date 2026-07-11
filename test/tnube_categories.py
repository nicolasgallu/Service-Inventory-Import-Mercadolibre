import json
import requests
from app.service.secrets import tienda_nube_secrets

ACCESS_TOKEN, STORE_ID = tienda_nube_secrets()

headers = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "User-Agent": "MyApp (tu@email.com)",
    "Content-Type": "application/json",
}

payload = {
    "name": {
        "es": "JUGUETERIA"
    },
    "parent": None
}

response = requests.post(
    f"https://api.tiendanube.com/v1/{STORE_ID}/categories",
    headers=headers,
    json=payload,
)

print("STATUS:", response.status_code)
print("BODY:", response.text)

if response.status_code == 201:
    category = response.json()

    result = {
        "id": category["id"],
        "name": category["name"]["es"],
        "data": json.dumps(
            {
                "name": category["name"],
                "handle": category["handle"],
                "parent": category["parent"],
                "seo_title": category.get("seo_title", {}),
                "created_at": category["created_at"],
                "updated_at": category["updated_at"],
                "visibility": category["visibility"],
                "description": category["description"],
                "subcategories": category["subcategories"],
                "seo_description": category.get("seo_description", {}),
                "visibility_updated_at": category["visibility_updated_at"],
                "google_shopping_category": category["google_shopping_category"],
            },
            ensure_ascii=False,
        ),
    }

    print(result)