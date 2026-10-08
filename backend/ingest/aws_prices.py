"""
Usage: python -m ingest.aws_prices "US East (N. Virginia)"
Region *names* (as AWS's Pricing API uses them), not region codes — see REGION_NAME_MAP.
"""
import sys
import json
import boto3
from db.connection import get_conn

REGION_NAME_MAP = {
    "US East (N. Virginia)": "us-east-1",
    "US West (Oregon)": "us-west-2",
    "US East (Ohio)": "us-east-2",
}

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


def extract_price_rows(product: dict, region_code: str) -> list[dict]:
    attrs = product["product"]["attributes"]
    if attrs.get("tenancy") != "Shared" or attrs.get("capacitystatus") != "Used":
        return []
    if attrs.get("marketoption") != "OnDemand" or attrs.get("locationType") != "AWS Region":
        return []

    on_demand = product.get("terms", {}).get("OnDemand", {})
    rows = []
    for term in on_demand.values():
        for dim in term["priceDimensions"].values():
            price = float(dim["pricePerUnit"]["USD"])
            if price <= 0:
                continue
            rows.append({
                "provider": "aws",
                "region": region_code,
                "instance_type": attrs["instanceType"],
                "operating_system": attrs["operatingSystem"],
                "pre_installed_sw": attrs.get("preInstalledSw", "NA"),
                "license_model": attrs.get("licenseModel"),
                "tenancy": attrs.get("tenancy"),
                "capacity_status": attrs.get("capacitystatus"),
                "purchase_option": "on_demand",
                "price_per_hour_usd": price,
                "sku_code": product["product"]["sku"],
                "effective_date": term.get("effectiveDate", "").split("T")[0] or None,
                "raw_payload": json.dumps(product),
            })
    return rows


def fetch_and_normalize(location_name: str, pre_installed_sw: str = "NA") -> list[dict]:
    region_code = REGION_NAME_MAP.get(location_name, location_name)
    pricing = boto3.client("pricing", region_name="us-east-1")
    paginator = pricing.get_paginator("get_products")
    rows = []
    for page in paginator.paginate(
        ServiceCode="AmazonEC2",
        Filters=[
            {"Type": "TERM_MATCH", "Field": "location", "Value": location_name},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
            {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": pre_installed_sw},
        ],
        FormatVersion="aws_v1",
    ):
        for product_string in page["PriceList"]:
            rows.extend(extract_price_rows(json.loads(product_string), region_code))
    return rows


def run(location_names: list[str]):
    with get_conn() as conn:
        for location in location_names:
            for sw in ("NA", "SQL Std", "SQL Ent", "SQL Web"):
                rows = fetch_and_normalize(location, pre_installed_sw=sw)
                if not rows:
                    continue
                with conn.cursor() as cur:
                    cur.executemany(UPSERT_SQL, rows)
                conn.commit()
                print(f"[{location} / preInstalledSw={sw}] upserted {len(rows)} price rows")


if __name__ == "__main__":
    run(sys.argv[1:] or ["US East (N. Virginia)"])
