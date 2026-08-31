#{'id': 2000018157082356, 'created_at': '2026-08-27T23:41:00.000-04:00', 'status': 'paid', 'pack_id': 2000014745810943, 'meli_ids': ['MLA3685942124']}
#{'id': 2000018157836228, 'created_at': '2026-08-28T01:37:00.000-04:00', 'status': 'paid', 'pack_id': 2000014746630849, 'meli_ids': ['MLA3613022920']}
#{'id': 2000018199037156, 'created_at': '2026-08-30T21:17:59.000-04:00', 'status': 'paid', 'pack_id': None, 'meli_ids': ['MLA3686077252']}
#{'id': 2000018197719650, 'created_at': '2026-08-30T19:56:34.000-04:00', 'status': 'paid', 'pack_id': 2000014784759559, 'meli_ids': ['MLA3523631680']}

import requests

ACCESS_TOKEN = ""


ORDER_IDS = [
    "2000018157082356",
    "2000018157836228",
    "2000018199037156",
    "2000018197719650",
]

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}"
}


def get_order(order_id):
    url = f"https://api.mercadolibre.com/orders/{order_id}"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=10
    )

    if response.status_code != 200:
        print(f"❌ Order {order_id} → HTTP {response.status_code}")
        print(response.text)
        return None

    return response.json()


def get_product_code(item_id):
    url = f"https://api.mercadolibre.com/items/{item_id}"

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=10
    )

    if response.status_code != 200:
        print(f"❌ Item {item_id} → HTTP {response.status_code}")
        return None

    data = response.json()

    # Prefer seller SKU
    for attribute in data.get("attributes", []):
        if attribute.get("id") == "SELLER_SKU":
            value = attribute.get("value_name")
            if value:
                return value

    # Otherwise use GTIN
    for attribute in data.get("attributes", []):
        if attribute.get("id") == "GTIN":
            value = attribute.get("value_name")
            if value:
                return value

    return None


results = []

for order_id in ORDER_IDS:

    print(f"\n📦 Processing order: {order_id}")

    order = get_order(order_id)

    if not order:
        continue

    order_items = order.get("order_items", [])

    for order_item in order_items:

        item = order_item.get("item", {})
        item_id = item.get("id")

        if not item_id:
            print("⚠️ No item ID found")
            continue

        product_code = get_product_code(item_id)

        result = {
            "order_id": order_id,
            "meli_id": item_id,
            "product_code": product_code
        }

        results.append(result)

        print(f"   Meli ID:      {item_id}")
        print(f"   Product Code: {product_code or 'NOT FOUND'}")


print("\n" + "=" * 70)
print("FINAL RESULTS")
print("=" * 70)

for result in results:
    print(result)