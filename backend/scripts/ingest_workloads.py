"""
Usage: python scripts/ingest_workloads.py path/to/Observed-Infrastructure.xlsx
"""
import sys
import json
from db.connection import get_conn
from adapters.azure_migrate_xlsx import build_workloads

UPSERT_SQL = """
INSERT INTO workload (id, group_name, asset, server_name, ip_address, os, os_version,
    sql_edition, sql_version, on_time_pct, observed_vcpu, cpu_util_pct, cpu_confidence,
    mem_provisioned_gb, mem_peak_gb, storage_gb, iops_peak, disk_throughput_mbps,
    net_mbps_peak, net_confidence, raw_row)
VALUES (%(id)s, %(group_name)s, %(asset)s, %(server_name)s, %(ip_address)s, %(os)s,
    %(os_version)s, %(sql_edition)s, %(sql_version)s, %(on_time_pct)s, %(observed_vcpu)s,
    %(cpu_util_pct)s, %(cpu_confidence)s, %(mem_provisioned_gb)s, %(mem_peak_gb)s,
    %(storage_gb)s, %(iops_peak)s, %(disk_throughput_mbps)s, %(net_mbps_peak)s,
    %(net_confidence)s, %(raw_row)s)
ON CONFLICT (id) DO UPDATE SET
    cpu_util_pct = EXCLUDED.cpu_util_pct,
    mem_provisioned_gb = EXCLUDED.mem_provisioned_gb,
    mem_peak_gb = EXCLUDED.mem_peak_gb,
    storage_gb = EXCLUDED.storage_gb,
    iops_peak = EXCLUDED.iops_peak,
    disk_throughput_mbps = EXCLUDED.disk_throughput_mbps,
    net_mbps_peak = EXCLUDED.net_mbps_peak,
    raw_row = EXCLUDED.raw_row,
    updated_at = now();
"""


def run(path: str):
    rows = build_workloads(path)
    for r in rows:
        r["raw_row"] = json.dumps(r, default=str)

    with get_conn() as conn, conn.cursor() as cur:
        cur.executemany(UPSERT_SQL, rows)
        conn.commit()
    print(f"Upserted {len(rows)} workloads from {path}")


if __name__ == "__main__":
    run(sys.argv[1])
