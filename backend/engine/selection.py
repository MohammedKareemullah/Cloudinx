import yaml
import functools
from config.settings import (
    CPU_PERF_RATIO_PATH, MEM_PER_VCPU_MEMORY_OPTIMIZED_THRESHOLD,
    MEM_PER_VCPU_COMPUTE_OPTIMIZED_THRESHOLD, GENERAL_PURPOSE_FAMILY_PREFIXES,
    MEMORY_OPTIMIZED_FAMILY_PREFIXES, COMPUTE_OPTIMIZED_FAMILY_PREFIXES,
    BURSTABLE_FAMILY_PREFIXES,
)
from engine.sizing import required_vcpu_for_family

SCENARIO_WEIGHTS = {
    "cost":        {"cost": 0.55, "fit": 0.20, "perf": 0.05, "affinity": 0.20},
    "balanced":    {"cost": 0.30, "fit": 0.30, "perf": 0.20, "affinity": 0.20},
    "performance": {"cost": 0.10, "fit": 0.20, "perf": 0.50, "affinity": 0.20},
}


@functools.lru_cache(maxsize=1)
def _load_ratio_table() -> dict:
    with open(CPU_PERF_RATIO_PATH) as f:
        return yaml.safe_load(f)


def _family_category(family: str, provider: str = "aws") -> str:
    f = family.lower()
    if provider == "azure":
        if f.startswith("b"):
            return "burstable"
        if f.startswith(("e", "m")):
            return "memory"
        if f.startswith("f"):
            return "compute"
        if f.startswith(("d", "a")):
            return "general"
        return "other"
    if f.startswith(BURSTABLE_FAMILY_PREFIXES):
        return "burstable"
    if f.startswith(MEMORY_OPTIMIZED_FAMILY_PREFIXES):
        return "memory"
    if f.startswith(COMPUTE_OPTIMIZED_FAMILY_PREFIXES):
        return "compute"
    if f.startswith(GENERAL_PURPOSE_FAMILY_PREFIXES):
        return "general"
    return "other"


def preferred_category(req, workload: dict) -> str:
    """Derived from the requirement's mem:vCPU ratio — the actual driver of family choice
    (confirmed against the reference export: 71% of real recommendations were memory-bound,
    and almost none of those workloads had SQL Server installed). SQL presence still nudges
    toward memory-optimized as a secondary signal, since licensing/perf docs commonly
    recommend it, but it's no longer the only signal."""
    approx_vcpu = max(1, req.cpu_demand_cores)  # rough, category-selection only
    ratio = req.mem_gb / approx_vcpu
    if ratio >= MEM_PER_VCPU_MEMORY_OPTIMIZED_THRESHOLD or workload.get("sql_edition"):
        return "memory"
    if ratio <= MEM_PER_VCPU_COMPUTE_OPTIMIZED_THRESHOLD:
        return "compute"
    return "general"


def passes_hard_filters(sku: dict, req, workload: dict, scenario: str):
    ratio_table = _load_ratio_table()
    req_vcpu = required_vcpu_for_family(req, sku["family"], scenario, ratio_table)

    if sku["vcpu"] < req_vcpu:
        return False, "vcpu", req_vcpu
    if sku["memory_gib"] < req.mem_gb:
        return False, "memory", req_vcpu
    if req.iops and (sku.get("ebs_max_iops") or 0) < req.iops:
        return False, "iops", req_vcpu
    if req.disk_mbps and (sku.get("ebs_max_mbps") or 0) < req.disk_mbps:
        return False, "disk_throughput", req_vcpu
    net_cap = sku.get("network_peak_gbps")
    if req.net_gbps and net_cap is not None and net_cap < req.net_gbps:
        return False, "network", req_vcpu
    if workload["os"] == "windows" and sku.get("architecture") not in ("x86_64", None):
        return False, "architecture", req_vcpu
    if sku.get("burstable") and workload.get("on_time_pct", 100) == 100:
        return False, "burstable_not_suited_for_prod", req_vcpu
    return True, None, req_vcpu


def shortfall_score(sku: dict, req, workload: dict, scenario: str) -> float:
    """How far a SKU falls short of the requirement, summed across dimensions, each
    normalized as a fraction of what's needed. Used only for the hardware-mapping
    fallback, to pick the LEAST-wrong SKU when nothing is fully fit for purpose —
    mirroring Cloudamize's own documented fallback behavior rather than returning nothing."""
    ratio_table = _load_ratio_table()
    req_vcpu = required_vcpu_for_family(req, sku["family"], scenario, ratio_table)
    total = 0.0
    if sku["vcpu"] < req_vcpu:
        total += (req_vcpu - sku["vcpu"]) / req_vcpu
    if sku["memory_gib"] < req.mem_gb:
        total += (req.mem_gb - sku["memory_gib"]) / req.mem_gb
    if req.iops and (sku.get("ebs_max_iops") or 0) < req.iops:
        total += (req.iops - (sku.get("ebs_max_iops") or 0)) / req.iops
    if req.disk_mbps and (sku.get("ebs_max_mbps") or 0) < req.disk_mbps:
        total += (req.disk_mbps - (sku.get("ebs_max_mbps") or 0)) / req.disk_mbps
    if req.net_gbps and (sku.get("network_peak_gbps") or 0) < req.net_gbps:
        total += (req.net_gbps - (sku.get("network_peak_gbps") or 0)) / req.net_gbps
    return total


def _norm(values, invert=False):
    lo, hi = min(values), max(values)
    if hi == lo:
        return [1.0] * len(values)
    return [(hi - v) / (hi - lo) if invert else (v - lo) / (hi - lo) for v in values]


def score_candidates(candidates, req, workload, scenario):
    weights = SCENARIO_WEIGHTS[scenario]
    preferred = preferred_category(req, workload)

    costs = [c["total_monthly"] for c in candidates]
    cost_scores = _norm(costs, invert=True)

    for c, cs in zip(candidates, cost_scores):
        req_vcpu = c.pop("_req_vcpu", None) or 1
        fit = max(0.0, 1 - abs((c["vcpu"] - req_vcpu) / max(req_vcpu, 1)))
        perf = 1.0 if c.get("current_generation") else 0.6
        affinity = 1.0 if _family_category(c["family"], c.get("provider", "aws")) == preferred else 0.5
        c["score_breakdown"] = {"cost": round(cs, 3), "fit": round(fit, 3),
                                 "perf": perf, "affinity": affinity}
        c["total_score"] = round(
            weights["cost"] * cs + weights["fit"] * fit +
            weights["perf"] * perf + weights["affinity"] * affinity, 4)
    return sorted(candidates, key=lambda c: c["total_score"], reverse=True)
