"""
Lazy, on-demand catalog/price ingestion. This is what lets a user pick ANY region in the
API without you having pre-run a CLI ingestion command for it — the first request for a new
(provider, region) pair pays a one-time ingestion cost; every request after that is instant,
since the data is cached in Postgres exactly like a pre-ingested region.
"""
from db import repository as repo
from config.aws_regions import AWS_REGION_LOCATION_NAMES


def ensure_catalog(provider: str, region: str):
    if repo.catalog_exists(provider, region):
        return {"ingested": False, "reason": "already_cached"}

    if provider == "aws":
        from ingest.aws_instance_types import run as ingest_types
        from ingest.aws_prices import run as ingest_prices
        location = AWS_REGION_LOCATION_NAMES.get(region)
        if not location:
            raise ValueError(
                f"Region '{region}' isn't in config/aws_regions.py's AWS_REGION_LOCATION_NAMES map "
                "— AWS's pricing API needs a location NAME, not just the region code, and there's "
                "no programmatic way to derive one from the other. Add the mapping and retry."
            )
        ingest_types([region])
        ingest_prices([location])
        return {"ingested": True, "provider": "aws", "region": region, "location": location}

    if provider == "azure":
        from ingest.azure_vm_skus import run as ingest_types
        from ingest.azure_prices import run as ingest_prices
        ingest_types([region])
        ingest_prices([region])
        return {"ingested": True, "provider": "azure", "region": region}

    raise ValueError(f"Unknown provider '{provider}' — expected 'aws' or 'azure'.")
