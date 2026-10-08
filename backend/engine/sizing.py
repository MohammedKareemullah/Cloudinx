"""
Sizing now separates two things that used to be conflated:
  1. Raw on-prem demand (cpu_demand_cores, mem_gb, iops, disk_mbps, net_gbps) — computed once,
     independent of any target instance.
  2. The conversion of that demand into a required vCPU count for a SPECIFIC candidate family —
     done in selection.py, per-candidate, using the calibrated cpu_perf_ratio table. A fixed
     "requirement.vcpu" doesn't make sense once different target families have different
     performance-per-vCPU (confirmed directly from the Cloudamize reference export: ~0.37 for
     r8i-flex/m8i-flex, ~0.26 for r8a/m8a, ~0.7 for t3/t3a — one flat number was never correct).
"""
from dataclasses import dataclass

@dataclass
class Requirement:
    cpu_demand_cores: float   # raw demand, in "on-prem core units" — NOT a vCPU count yet
    mem_gb: float
    iops: int | None
    disk_mbps: float | None
    net_gbps: float | None
    confidence: str
    notes: list

SCENARIO_CONFIG = {
    "cost":        {"target_cpu_util": 0.80, "target_mem_util": 0.85},
    "balanced":    {"target_cpu_util": 0.70, "target_mem_util": 0.80},
    "performance": {"target_cpu_util": 0.55, "target_mem_util": 0.70},
}

def derive_requirements(workload: dict, scenario: str) -> Requirement:
    cfg = SCENARIO_CONFIG[scenario]
    notes = []

    cpu_pct = workload["cpu_util_pct"]
    if cpu_pct > 100:
        notes.append(f"cpu_util_pct clamped from {cpu_pct} to 100 (source data quality issue)")
        cpu_pct = 100.0
    if workload.get("cpu_confidence", "point_in_time") == "point_in_time":
        notes.append("cpu_util is a single point-in-time reading, not avg/p95/peak — "
                      "treat sizing as directional, not exact")

    # Raw demand only — no generic inflate/deflate buffer here. The real performance
    # normalization is family-specific and happens in selection.py at filter time.
    cpu_demand_cores = workload["observed_vcpu"] * (cpu_pct / 100)

    mem_peak = workload.get("mem_peak_gb")
    if mem_peak:
        mem_basis = mem_peak
    else:
        mem_basis = workload["mem_provisioned_gb"] * 1.15
        notes.append("no peak memory reading — used provisioned x1.15 buffer")
    req_mem = round(mem_basis / cfg["target_mem_util"], 1)

    iops = int(workload["iops_peak"] * 1.2) if workload.get("iops_peak") else None
    disk_mbps = workload.get("disk_throughput_mbps")
    disk_mbps = round(disk_mbps * 1.2, 1) if disk_mbps else None

    net_gbps = None
    if workload.get("net_mbps_peak"):
        net_gbps = round(workload["net_mbps_peak"] * 1.3 / 1000, 4)
        notes.append("network peak derived from monthly GB + predicted-peak% heuristic, not measured Mbps")

    confidence = "low" if workload.get("cpu_confidence") == "point_in_time" else "medium"

    return Requirement(cpu_demand_cores=round(cpu_demand_cores, 3), mem_gb=req_mem, iops=iops,
                        disk_mbps=disk_mbps, net_gbps=net_gbps, confidence=confidence, notes=notes)


def required_vcpu_for_family(req: Requirement, family: str, scenario: str,
                              ratio_table: dict) -> int:
    """Convert raw demand into a vCPU count for a SPECIFIC target family, using its
    calibrated performance ratio. This replaces the old fixed req.vcpu."""
    ratio = ratio_table.get("families", {}).get(family, ratio_table.get("default", 1.0))
    target_util = SCENARIO_CONFIG[scenario]["target_cpu_util"]
    cloud_demand = req.cpu_demand_cores * ratio
    return max(1, -(-int(cloud_demand / target_util) // 1))  # ceil
