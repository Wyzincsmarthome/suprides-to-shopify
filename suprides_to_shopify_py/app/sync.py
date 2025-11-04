import os, sys, re, json

from app.suprides_client import get_by_ean
from app.shopify_client import (
    find_variant_by_barcode,
    product_create_minimal,
    variants_bulk_update,
    inventory_set_quantities,
)

def as_bool(val, default=False):
    if val is None or val == "":
        return default
    return str(val).lower() == "true"

def read_eans(path='data/productsList.txt'):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
    except FileNotFoundError:
        print(f"[WARN] Ficheiro {path} não encontrado. Nada a fazer.")
        return []
    if not content:
        return []
    if content.startswith('['):
        arr = json.loads(content)
        eans = [str(x).strip() for x in arr if str(x).strip()]
    else:
        eans = []
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'): 
                continue
            if re.fullmatch(r"\d+", line):
                eans.append(line)
    # dedup
    seen, out = set(), []
    for e in eans:
        if e not in seen:
            seen.add(e); out.append(e)
    return out

def main():
    DRY_RUN = as_bool(os.getenv('DRY_RUN', 'true'), True)
    PUBLISH = as_bool(os.getenv('PUBLISH_TO_ONLINE_STORE', 'false'), False)
    LOCATION_ID = os.getenv('SHOPIFY_LOCATION_ID')  # obrigatório para stock
    DEFAULT_VENDOR = os.getenv('DEFAULT_VENDOR', 'Suprides')
    PRICE_SOURCE = os.getenv('PRICE_SOURCE', 'pvpr')

    if not LOCATION_ID:
        print('[ERRO] SHOPIFY_LOCATION_ID em falta.')
        sys.exit(1)

    eans = read_eans()
    if not eans:
        print('[INFO] Lista de EANs vazia. Terminado.')
        return 0

    processed = success = errors = skipped = 0

    for ean in eans:
        processed += 1
        print(f"\n▶️  EAN {ean}")
        try:
            sup = get_by_ean(ean)
            if not sup:
                print(f"   ↪️ Sem dados do fornecedor. Ignorado.")
                skipped += 1
                continue

            sup['ean'] = str(sup.get('ean') or ean)
            sup['sku'] = str(sup.get('sku') or sup['ean'])
            price_val = float(sup.get(PRICE_SOURCE, 0) or 0)
            sup['pvpr'] = price_val
            stock_val = int(sup.get('stock') or 0)
            sup['stock'] = stock_val

            # Tentar UPDATE: encontrar variante por barcode
            variant = find_variant_by_barcode(sup['ean'])
            if variant:
                if DRY_RUN:
                    print(f"[DRY_RUN] UPDATE -> {sup['ean']} price={price_val:.2f} stock={stock_val}")
                    success += 1
                    continue
                product_id = variant['product']['id']
                updated_variant = variants_bulk_update(product_id, sup['sku'], sup['ean'], f"{price_val:.2f}")
                inventory_set_quantities(updated_variant['inventoryItem']['id'], LOCATION_ID, stock_val)
                print(f"   ✅ Atualizado {sup['ean']}")
                success += 1
                continue

            # Se não existe, criar
            if DRY_RUN:
                print(f"[DRY_RUN] CREATE -> {sup['ean']} title='{sup.get('title')}' price={price_val:.2f} stock={stock_val}")
                success += 1
                continue

            product_id = product_create_minimal(sup.get('title') or sup['ean'], DEFAULT_VENDOR, sup.get('description_html') or '', PUBLISH)
            updated_variant = variants_bulk_update(product_id, sup['sku'], sup['ean'], f"{price_val:.2f}")
            inventory_set_quantities(updated_variant['inventoryItem']['id'], LOCATION_ID, stock_val)
            print(f"   🆕 Criado {sup['ean']}")
            success += 1

        except Exception as e:
            print(f"   ❌ Erro: {e}")
            errors += 1

    print("\n📊 Resumo:")
    print(f"   • Processados: {processed}")
    print(f"   • Sucessos:   {success}")
    print(f"   • Erros:      {errors}")
    print(f"   • Ignorados:  {skipped}")
    return 0 if errors == 0 else 1

if __name__ == '__main__':
    raise SystemExit(main())
