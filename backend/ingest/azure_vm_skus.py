"""
Usage: python -m ingest.azure_vm_skus eastus westeurope uaenorth

Azure's region naming is actually simpler than AWS's: the same short code (e.g. "eastus")
is used for both the catalog API and the pricing API (armRegionName), unlike AWS which
needs a separate code<->location-name map. One less thing to get wrong here.

Mapped fields, and where they genuinely differ from AWS (worth knowing, not just copying):
  - network_baseline_gbps / network_peak_gbps are left NULL. Azure's ResourceSkus API does
    not reliably publish per-size network bandwidth the way AWS's NetworkInfo does, so the
    network hard filter is skipped for Azure SKUs rather than falsely rejecting everything
    (see the fix in engine/selection.py).
  - ebs_max_iops / ebs_max_mbps are populated from Azure's "UncachedDiskIOPS" and
    "UncachedDiskBytesPerSecond" capabilities — the closest semantic equivalent to AWS's
    EBS-optimized max IOPS/throughput (the ceiling on attached managed-disk performance).
  - current_generation is approximated as True for everything returned (Azure doesn't
    expose a clean current/previous-generation flag the way AWS does); refine later if
    you want to deprioritize old-generation sizes explicitly.
"""
import sys
import re
import json
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from db.connection import get_conn
from config.settings import AZURE_SUBSCRIPTION_ID, CATALOG_FAMILY_DENYLIST_PREFIXES

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
    raw_payload = EXCLUDED.raw_payload, fetched_at = now();
"""


def _derive_family(size_name: str) -> str:
    """'Standard_E8s_v5' -> 'Es_v5' — strips only the leading vCPU-count digits, keeping the
    series letter and version suffix intact, so v5 and v6 of the same series stay distinct
    families (stripping ALL digits would collapse different generations together)."""
    name = size_name.replace("Standard_", "")
    return re.sub(r"^([A-Za-z]+)\d+", r"\1", name) or name


def normalize_sku(sku, region: str) -> dict | None:
    if sku.resource_type != "virtualMachines":
        return None
    capabilities = {c.name: c.value for c in (sku.capabilities or [])}
    if any(r.type == "Location" for r in (sku.restrictions or [])):
        return None  # not actually available in this region for this subscription

    vcpu = capabilities.get("vCPUs")
    mem = capabilities.get("MemoryGB")
    if not vcpu or not mem:
        return None

    arch_raw = capabilities.get("CpuArchitectureType", "x64")
    architecture = "arm64" if "arm" in arch_raw.lower() else "x86_64"
    family = _derive_family(sku.name)
    burstable = sku.name.replace("Standard_", "").startswith("B")

    def _num(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    uncached_iops = _num(capabilities.get("UncachedDiskIOPS"))
    uncached_bps = _num(capabilities.get("UncachedDiskBytesPerSecond"))

    return {
        "provider": "azure",
        "region": region,
        "instance_type": sku.name,
        "family": family,
        "current_generation": True,
        "vcpu": int(float(vcpu)),
        "memory_gib": round(float(mem), 2),
        "architecture": architecture,
        "processor": None,
        "burstable": burstable,
        "network_baseline_gbps": None,
        "network_peak_gbps": None,
        "ebs_baseline_iops": None,
        "ebs_max_iops": int(uncached_iops) if uncached_iops else None,
        "ebs_baseline_mbps": None,
        "ebs_max_mbps": round(uncached_bps / 1_000_000, 2) if uncached_bps else None,
        "instance_storage_gb": _num(capabilities.get("MaxResourceVolumeMB")) and
                                round(_num(capabilities.get("MaxResourceVolumeMB")) / 1024, 2),
        "hypervisor": capabilities.get("HyperVGenerations"),
        "raw_payload": json.dumps({"name": sku.name, "family": sku.family, "size": sku.size,
                                    "capabilities": capabilities}),
    }


def fetch_and_normalize(region: str) -> list[dict]:
    credential = DefaultAzureCredential()
    client = ComputeManagementClient(credential, AZURE_SUBSCRIPTION_ID)
    rows = []
    for sku in client.resource_skus.list(filter=f"location eq '{region}'"):
        row = normalize_sku(sku, region)
        if not row:
            continue
        if any(row["family"].lower().startswith(p) for p in CATALOG_FAMILY_DENYLIST_PREFIXES if p):
            continue
        rows.append(row)
    return rows


def run(regions: list[str]):
    with get_conn() as conn:
        for region in regions:
            rows = fetch_and_normalize(region)
            with conn.cursor() as cur:
                cur.executemany(UPSERT_SQL, rows)
            conn.commit()
            print(f"[{region}] upserted {len(rows)} Azure VM sizes "
                  f"(families: {sorted(set(r['family'] for r in rows))[:10]}...)")


if __name__ == "__main__":
    run(sys.argv[1:] or ["eastus"])
