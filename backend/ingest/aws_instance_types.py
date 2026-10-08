"""
Usage: python -m ingest.aws_instance_types us-east-1 us-west-2
"""
import sys
import re
import json
import boto3
from db.connection import get_conn
from config.settings import CATALOG_FAMILY_DENYLIST_PREFIXES

UPSERT_SQL = """
INSERT INTO instance_sku (provider, region, instance_type, family, current_generation,
    vcpu, memory_gib, architecture, processor, burstable, network_baseline_gbps,
    network_peak_gbps, ebs_baseline_iops, ebs_max_iops, ebs_baseline_mbps, ebs_max_mbps,
    instance_storage_gb, hypervisor, raw_payload)
VALUES (%(provider)s, %(region)s, %(instance_type)s, %(family)s, %(current_generation)s,
    %(vcpu)s, %(memory_gib)s, %(architecture)s, %(processor)s, %(burstable)s,
    %(network_baseline_gbps)s, %(network_peak_gbps)s, %(ebs_baseline_iops)s,
    %(ebs_max_iops)s, %(ebs_baseline_mbps)s, %(ebs_max_mbps)s, %(instance_storage_gb)s,
    %(hypervisor)s, %(raw_payload)s)
ON CONFLICT (provider, region, instance_type) DO UPDATE SET
    vcpu = EXCLUDED.vcpu, memory_gib = EXCLUDED.memory_gib,
    ebs_max_iops = EXCLUDED.ebs_max_iops, ebs_max_mbps = EXCLUDED.ebs_max_mbps,
    network_peak_gbps = EXCLUDED.network_peak_gbps,
    raw_payload = EXCLUDED.raw_payload, fetched_at = now();
"""


def parse_network_gbps(network_info: dict):
    cards = network_info.get("NetworkCards") or []
    if cards:
        return cards[0].get("BaselineBandwidthInGbps"), cards[0].get("PeakBandwidthInGbps")
    m = re.search(r"([\d.]+)\s*Gigabit", network_info.get("NetworkPerformance", ""))
    if m:
        val = float(m.group(1))
        return val, val
    return None, None


def normalize_instance(item: dict, region: str) -> dict:
    vcpu_info = item.get("VCpuInfo", {})
    mem_info = item.get("MemoryInfo", {})
    ebs_info = item.get("EbsInfo", {}).get("EbsOptimizedInfo", {})
    net_info = item.get("NetworkInfo", {})
    proc_info = item.get("ProcessorInfo", {})
    storage_info = item.get("InstanceStorageInfo", {}) if item.get("InstanceStorageSupported") else {}

    net_baseline, net_peak = parse_network_gbps(net_info)
    instance_type = item["InstanceType"]

    return {
        "provider": "aws",
        "region": region,
        "instance_type": instance_type,
        "family": instance_type.split(".")[0],
        "current_generation": item.get("CurrentGeneration", False),
        "vcpu": vcpu_info.get("DefaultVCpus"),
        "memory_gib": round(mem_info.get("SizeInMiB", 0) / 1024, 2),
        "architecture": (proc_info.get("SupportedArchitectures") or [None])[0],
        "processor": proc_info.get("Manufacturer"),
        "burstable": item.get("BurstablePerformanceSupported", False),
        "network_baseline_gbps": net_baseline,
        "network_peak_gbps": net_peak,
        "ebs_baseline_iops": ebs_info.get("BaselineIops"),
        "ebs_max_iops": ebs_info.get("MaximumIops"),
        "ebs_baseline_mbps": ebs_info.get("BaselineThroughputInMBps"),
        "ebs_max_mbps": ebs_info.get("MaximumThroughputInMBps"),
        "instance_storage_gb": storage_info.get("TotalSizeInGB"),
        "hypervisor": item.get("Hypervisor"),
        "raw_payload": json.dumps(item),
    }


def fetch_and_normalize(region: str) -> list[dict]:
    ec2 = boto3.client("ec2", region_name=region)
    paginator = ec2.get_paginator("describe_instance_types")
    rows = []
    for page in paginator.paginate():
        for item in page["InstanceTypes"]:
            if not item.get("SupportedInRegion", True) or not item.get("CurrentGeneration", True):
                continue
            family = item["InstanceType"].split(".")[0]
            if any(family.startswith(p) for p in CATALOG_FAMILY_DENYLIST_PREFIXES if p):
                continue
            rows.append(normalize_instance(item, region))
    return rows


def run(regions: list[str]):
    with get_conn() as conn:
        for region in regions:
            rows = fetch_and_normalize(region)
            with conn.cursor() as cur:
                cur.executemany(UPSERT_SQL, rows)
            conn.commit()
            print(f"[{region}] upserted {len(rows)} instance types "
                  f"(families: {sorted(set(r['family'] for r in rows))})")


if __name__ == "__main__":
    run(sys.argv[1:] or ["us-east-1"])
