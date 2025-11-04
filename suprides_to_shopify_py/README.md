# Suprides → Shopify (Python)

**Objetivo**: Ler EANs a partir de `data/productsList.txt`, obter dados do fornecedor Suprides por EAN e criar/atualizar produtos na Shopify (por `barcode == EAN`), com execução no **GitHub Actions** e, depois, em **Render Cron**.

## Pipeline
1. Seleção: `data/productsList.txt` (um EAN por linha ou JSON array).
2. Suprides: `app/suprides_client.py` devolve `{ ean, sku, title, description_html, brand, pvpr, stock }`.
3. Shopify (GraphQL): `app/shopify_client.py` procura variante por `barcode`, atualiza preço/stock; se não existir, cria produto e define a variante com `barcode`.
4. Orquestração: `app/sync.py` respeita `DRY_RUN` para corridas seguras e publica em Draft quando `PUBLISH_TO_ONLINE_STORE=false`.

## Variáveis de ambiente (via Secrets no GitHub/Render)
Ver `.env.example`. No GitHub Actions, mapeia os teus secrets atuais:
- `API_USER` → `SUPRIDES_USERNAME`
- `API_PASSWORD` → `SUPRIDES_PASSWORD`
- `API_TOKEN` → `SUPRIDES_TOKEN`
- `SHOPIFY_STORE_URL` (domínio, ex.: `08b4f4-5f.myshopify.com`) → `SHOPIFY_STORE_DOMAIN`
- `SHOPIFY_ACCESS_TOKEN`
- `SHOPIFY_LOCATION_ID`
- `DISCORD_WEBHOOK_URL` (opcional)

## Como correr no GitHub Actions
- Edita `data/productsList.txt` com 2–3 EANs de teste.
- Vai a **Actions → Sync Products → Run workflow**. Primeiro corre em `DRY_RUN=true`.
- Verifica logs. Quando validado, troca para `DRY_RUN=false`. Quando estiver ok em Draft, põe `PUBLISH_TO_ONLINE_STORE=true`.

## Execução local (opcional)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # preencher valores
python -m app.sync
```
