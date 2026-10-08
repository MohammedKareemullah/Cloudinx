"""
Usage: python -m ingest.azure_prices eastus westeurope uaenorth

Azure's Retail Prices API doesn't have a clean "operatingSystem" field like AWS's Pricing
API does — OS has to be inferred from productName/skuName (Windows pricing says so
explicitly; its absence means Linux, Azure's default VM pricing baseline). Spot and
Reservation entries are excluded here; only on-demand (priceType=Consumption) is ingested,
matching the AWS ingestion's current scope.
"""
import sys
import requests
from db.connection import get_conn

AZURE_PRICING_URL = "https://prices.azure.com/api/retail/prices"

UPSERT_SQL = """
INSERT INTO instance_price (provider, region, instance_type, operating_system, pre_installed_sw,
    license_model, tenancy, capacity_status, purchase_option, price_per_hour_usd, sku_code,
    effective_date, raw_payload)
VALUES (%(provider)s, %(region)s, %(instance_type)s, %(operating_system)s, %(pre_installed_sw)s,
    %(license_model)s, %(tenancy)s, %(capacity_status)s, %(purchase_option)s,
    %(price_per_hour_usd)s, %(sku_code)s, %(effective_date)s, %(raw_payload)s)
ON CONFLICT (provider, region, instance_type, operating_system, pre_installed_sw, purchase_option)
DO UPDATE SET price_per_hour_usd = EXCLUDED.price_per_hour_usd,
              effective_date = EXCLUDED.effective_date,
              raw_payload = EXCLUDED.raw_payload, fetched_at = now();
"""


def _infer_os(item: dict) -> str:
    text = f"{item.get('productName', '')} {item.get('skuName', '')}".lower()
    return "Windows" if "windows" in text else "Linux"


def _is_excluded(item: dict) -> bool:
    text = f"{item.get('productName', '')} {item.get('skuName', '')} {item.get('meterName', '')}".lower()
    return "spot" in text or "low priority" in text


def fetch_and_normalize(region: str, price_type: str = "Consumption") -> list[dict]:
    filters = [
        "serviceName eq 'Virtual Machines'",
        f"armRegionName eq '{region}'",
        f"priceType eq '{price_type}'",
    ]
    params = {"$filter": " and ".join(filters)}
    rows, url = [], AZURE_PRICING_URL

    while url:
        response = requests.get(url, params=params if url == AZURE_PRICING_URL else None, timeout=30)
        response.raise_for_status()
        data = response.json()

        for item in data.get("Items", []):
            if _is_excluded(item):
                continue
            price = item.get("retailPrice")
            if not price or price <= 0:
                continue
            rows.append({
                "provider": "azure",
                "region": region,
                "instance_type": item.get("armSkuName"),
                "operating_system": _infer_os(item),
                "pre_installed_sw": "NA",
                "license_model": None,
                "tenancy": "Shared",
                "capacity_status": "Used",
                "purchase_option": "on_demand",
                "price_per_hour_usd": price,
                "sku_code": item.get("meterId"),
                "effective_date": (item.get("effectiveStartDate") or "").split("T")[0] or None,
                "raw_payload": __import__("json").dumps(item),
            })
        url = data.get("NextPageLink")

    return rows


def run(regions: list[str]):
    with get_conn() as conn:
        for region in regions:
            rows = fetch_and_normalize(region)
            with conn.cursor() as cur:
                cur.executemany(UPSERT_SQL, rows)
            conn.commit()
            print(f"[{region}] upserted {len(rows)} Azure price rows")


if __name__ == "__main__":
    run(sys.argv[1:] or ["eastus"])
