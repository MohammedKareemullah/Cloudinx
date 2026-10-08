"""
Usage:
    python -m scripts.generate_migration_plan --region me-central-1 [--group-name X] \
        [--scenarios cost balanced performance] [--csv-out migration_plan.csv]
"""
import argparse
import csv
from engine.migration_plan import build_plan, print_plan


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region", required=True)
    p.add_argument("--group-name", default=None)
    p.add_argument("--scenarios", nargs="+", default=["cost", "balanced", "performance"])
    p.add_argument("--csv-out", default=None)
    args = p.parse_args()

    plan = build_plan(args.region, args.group_name, args.scenarios)
    print_plan(plan)

    if args.csv_out:
        with open(args.csv_out, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(plan["line_items"][0].keys()))
            writer.writeheader()
            writer.writerows(plan["line_items"])
        print(f"\nLine items written to {args.csv_out}")


if __name__ == "__main__":
    main()
