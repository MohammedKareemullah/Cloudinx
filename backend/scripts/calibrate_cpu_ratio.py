"""
Calibrate config/cpu_perf_ratio.yaml from a reference assessment export (e.g. a Cloudamize
"Dashboard - Workload (On-Demand)" export) that already contains recommended instances.

Usage:
    python -m scripts.calibrate_cpu_ratio path/to/reference_export.xlsx [--out config/cpu_perf_ratio.yaml]

Re-run this whenever you get a new reference export (a different customer's assessment, or a
refreshed one) to keep the ratio table current — it's a five-line regression, not a trained
model, so it costs nothing to redo.
"""
import sys
import argparse
import statistics
import yaml
from collections import defaultdict
import openpyxl


def calibrate(path: str, sheet: str = "Compute", min_samples: int = 3) -> dict:
    wb = openpyxl.load_workbook(path, data_only=True)
    ws = wb[sheet]
    hdr = list(ws.iter_rows(min_row=2, max_row=2, values_only=True))[0]
    idx = {h: i for i, h in enumerate(hdr)}
    required = ["Observed vCPU", "Current CPU Utilization (%)", "Predicted CPU Utilization (%)",
                "Recommended vCPU", "Recommended Instance"]
    missing = [c for c in required if c not in idx]
    if missing:
        raise ValueError(f"Reference export is missing expected columns: {missing}")

    by_family = defaultdict(list)
    for r in ws.iter_rows(min_row=3, values_only=True):
        obs_vcpu, cur, pred, rec_vcpu = (r[idx["Observed vCPU"]], r[idx["Current CPU Utilization (%)"]],
                                          r[idx["Predicted CPU Utilization (%)"]], r[idx["Recommended vCPU"]])
        rec_instance = r[idx["Recommended Instance"]]
        if not (obs_vcpu and cur and pred and rec_vcpu and rec_instance) or cur == 0:
            continue
        onprem = obs_vcpu * (min(cur, 100) / 100)
        if onprem <= 0:
            continue
        cloud = rec_vcpu * (pred / 100)
        ratio = cloud / onprem
        # Exclude rows that hit the smallest-instance-size floor — the ratio there reflects
        # rounding to a minimum size, not the true CPU performance factor.
        if rec_vcpu <= 2 and obs_vcpu <= 2:
            continue
        family = str(rec_instance).split(".")[0]
        by_family[family].append(ratio)

    table = {f: round(statistics.median(v), 3) for f, v in by_family.items() if len(v) >= min_samples}
    overall = [v for vv in by_family.values() for v in vv]
    if not overall:
        raise ValueError("No usable rows found — check the sheet/column names match your export.")

    return {
        "_comment": f"Per-target-family CPU performance ratio, calibrated from {path} "
                    f"({len(overall)} usable rows). ratio = cloud_vcpu_demand / onprem_core_demand. "
                    "A ratio < 1 means the target family's vCPU is faster than the source CPU.",
        "default": round(statistics.median(overall), 3),
        "families": table,
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("reference_file")
    p.add_argument("--sheet", default="Compute")
    p.add_argument("--out", default="config/cpu_perf_ratio.yaml")
    args = p.parse_args()

    result = calibrate(args.reference_file, args.sheet)
    with open(args.out, "w") as f:
        yaml.dump(result, f, sort_keys=False)
    print(f"Calibrated {len(result['families'])} families, default={result['default']}, "
          f"written to {args.out}")
    for fam, ratio in sorted(result["families"].items()):
        print(f"  {fam:14s} {ratio}")
