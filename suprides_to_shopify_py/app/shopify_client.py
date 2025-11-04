import os
import requests
from tenacity import retry, wait_exponential, stop_after_attempt

API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2025-01")
DOMAIN = os.environ["SHOPIFY_STORE_DOMAIN"].replace("https://","").replace("http://","").strip("/")
ACCESS_TOKEN = os.environ["SHOPIFY_ACCESS_TOKEN"]
GQL_URL = f"https://{DOMAIN}/admin/api/{API_VERSION}/graphql.json"
HEADERS = {"X-Shopify-Access-Token": ACCESS_TOKEN, "Content-Type": "application/json"}

def gql(query, variables=None):
    resp = requests.post(GQL_URL, json={"query": query, "variables": variables or {}}, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]

def find_variant_by_barcode(barcode: str):
    q = """
    query($q:String!){
      productVariants(first: 1, query: $q) {
        edges { node { id sku barcode price inventoryItem { id } product { id title } } }
      }
    }"""
    res = gql(q, {"q": f"barcode:{barcode}"})
    edges = res["productVariants"]["edges"]
    return edges[0]["node"] if edges else None

def product_create_minimal(title: str, vendor: str, description_html: str, published: bool):
    m = """
    mutation($input: ProductInput!) {
      productCreate(input: $input) {
        product { id title handle }
        userErrors { field message }
      }
    }"""
    input_ = {
      "title": title,
      "vendor": vendor,
      "descriptionHtml": description_html or "",
      "status": "ACTIVE" if published else "DRAFT",
    }
    res = gql(m, {"input": input_})
    ue = res["productCreate"]["userErrors"]
    if ue: raise RuntimeError(ue)
    return res["productCreate"]["product"]["id"]

def variants_bulk_update(product_id: str, sku: str, barcode: str, price: str):
    m = """
    mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
      productVariantsBulkUpdate(productId: $productId, variants: $variants) {
        product { id }
        productVariants { id sku barcode price inventoryItem { id } }
        userErrors { field message }
      }
    }"""
    vars_ = {
      "productId": product_id,
      "variants": [{
        "options": [],
        "sku": sku or barcode,
        "barcode": barcode,
        "price": price
      }]
    }
    res = gql(m, vars_)
    ue = res["productVariantsBulkUpdate"]["userErrors"]
    if ue: raise RuntimeError(ue)
    variants = res["productVariantsBulkUpdate"]["productVariants"]
    return variants[0]

def inventory_set_quantities(inventory_item_id: str, location_id: str, available_quantity: int):
    m = """
    mutation($input: InventorySetQuantitiesInput!) {
      inventorySetQuantities(input: $input) {
        userErrors { field message }
        inventoryAdjustmentGroup { createdAt reason referenceDocumentUri changes { name delta quantityAfterChange } }
      }
    }"""
    input_ = {
      "reason": "received",
      "changes": [{
        "name": "available",
        "inventoryItemId": inventory_item_id,
        "locationId": location_id,
        "delta": available_quantity,
      }],
      "ignoreCompareQuantity": True
    }
    res = gql(m, {"input": input_})
    ue = res["inventorySetQuantities"]["userErrors"]
    if ue: raise RuntimeError(ue)
    return True
