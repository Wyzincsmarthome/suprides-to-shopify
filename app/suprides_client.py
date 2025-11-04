import os
import requests

BASE = os.getenv("SUPRIDES_BASE_URL", "").rstrip("/")
USER = os.getenv("SUPRIDES_USERNAME")
PWD = os.getenv("SUPRIDES_PASSWORD")
TOKEN = os.getenv("SUPRIDES_TOKEN")

def _headers():
    if TOKEN:
        return {"Authorization": f"Bearer {TOKEN}"}
    return {}

def get_by_ean(ean: str) -> dict:
    if not BASE:
        raise RuntimeError("SUPRIDES_BASE_URL não definido")
    # Ajustar a rota conforme a API real da Suprides
    url = f"{BASE}/products?ean={ean}"
    r = requests.get(url, headers=_headers(), timeout=60)
    r.raise_for_status()
    js = r.json()
    if isinstance(js, list) and js:
        item = js[0]
    else:
        item = js or {}
    return {
        "ean": ean,
        "sku": item.get("sku") or ean,
        "title": item.get("title") or item.get("name") or ean,
        "description_html": item.get("description") or "",
        "brand": item.get("brand") or "Suprides",
        "pvpr": float(item.get("pvpr") or 0),
        "stock": int(item.get("stock") or 0),
    }
