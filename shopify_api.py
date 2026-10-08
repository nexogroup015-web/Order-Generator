import requests


def fetch_orders(store, token, limit=250):
    url = f"https://{store}/admin/api/2024-01/orders.json"
    headers = {"X-Shopify-Access-Token": token}
    params = {"status": "any", "limit": limit}

    orders = []
    while url:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        orders.extend(data.get("orders", []))

        link = response.headers.get("Link", "")
        url = None
        params = {}
        if 'rel="next"' in link:
            for part in link.split(","):
                if 'rel="next"' in part:
                    url = part.split(";")[0].strip().strip("<>")

    return orders
