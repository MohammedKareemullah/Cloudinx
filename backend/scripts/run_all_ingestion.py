"""
Usage:
    python scripts/run_all_ingestion.py --workload-file path/to/Observed-Infrastructure.xlsx \
        --aws-regions us-east-1 us-west-2 \
        --aws-locations "US East (N. Virginia)" "US West (Oregon)"

Run this once to (re)build the whole dataset: schema, workloads, AWS catalog, AWS prices.
Safe to re-run — every step is an upsert.
"""
import argparse
from db.connection import init_schema
from scripts.ingest_workloads import run as ingest_workloads
from ingest.aws_instance_types import run as ingest_catalog
from ingest.aws_prices import run as ingest_prices


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workload-file", required=True)
    parser.add_argument("--aws-regions", nargs="+", default=["us-east-1"])
    parser.add_argument("--aws-locations", nargs="+", default=["US East (N. Virginia)"])
    parser.add_argument("--skip-schema", action="store_true")
    args = parser.parse_args()

    if not args.skip_schema:
        print("== Applying schema ==")
        init_schema("db/schema.sql")

    print("== Ingesting workloads ==")
    ingest_workloads(args.workload_file)

    print("== Ingesting AWS instance catalog ==")
    ingest_catalog(args.aws_regions)

    print("== Ingesting AWS prices ==")
    ingest_prices(args.aws_locations)

    print("Done.")


if __name__ == "__main__":
    main()
