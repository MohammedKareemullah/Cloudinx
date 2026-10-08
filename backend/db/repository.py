import json
from db.connection import get_conn


def list_workloads(group_name: str | None = None) -> list[dict]:
    sql = "SELECT id, server_name, os, group_name FROM workload"
    params = []
    if group_name:
        sql += " WHERE group_name = %s"
        params.append(group_name)
    sql += " ORDER BY server_name"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def get_workload(workload_id: str) -> dict | None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, group_name, asset, server_name, ip_address, os, os_version, sql_edition, sql_version, on_time_pct, observed_vcpu, cpu_util_pct, cpu_confidence, mem_provisioned_gb, mem_peak_gb, storage_gb, iops_peak, disk_throughput_mbps, net_mbps_peak, net_confidence FROM workload WHERE id = %s", (workload_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def search_instances(region: str, min_vcpu: int, min_mem_gb: float,
                      min_iops: int | None = None, min_disk_mbps: float | None = None,
                      min_net_gbps: float | None = None, provider: str = "aws") -> list[dict]:
    sql = """
        SELECT provider, region, instance_type, family, current_generation, vcpu, memory_gib, architecture, processor, burstable, network_baseline_gbps, network_peak_gbps, ebs_baseline_iops, ebs_max_iops, ebs_baseline_mbps, ebs_max_mbps, instance_storage_gb FROM instance_sku
        WHERE provider = %s AND region = %s AND vcpu >= %s AND memory_gib >= %s
    """
    params = [provider, region, min_vcpu, min_mem_gb]
    if min_iops:
        sql += " AND COALESCE(ebs_max_iops, 0) >= %s"
        params.append(min_iops)
    if min_disk_mbps:
        sql += " AND COALESCE(ebs_max_mbps, 0) >= %s"
        params.append(min_disk_mbps)
    if min_net_gbps:
        sql += " AND COALESCE(network_peak_gbps, 0) >= %s"
        params.append(min_net_gbps)
    sql += " ORDER BY vcpu ASC"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def catalog_exists(provider: str, region: str) -> bool:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM instance_sku WHERE provider = %s AND region = %s LIMIT 1",
            (provider, region),
        )
        return cur.fetchone() is not None


def get_catalog(region: str, provider: str = "aws") -> list[dict]:
    """Full candidate set for a region — selection.py applies the remaining filters in Python
    since some (architecture/OS/burstable) depend on the workload, not just numeric thresholds."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT provider, region, instance_type, family, current_generation, vcpu, memory_gib, architecture, processor, burstable, network_baseline_gbps, network_peak_gbps, ebs_baseline_iops, ebs_max_iops, ebs_baseline_mbps, ebs_max_mbps, instance_storage_gb FROM instance_sku WHERE provider = %s AND region = %s",
            (provider, region),
        )
        return [dict(r) for r in cur.fetchall()]


def get_price(instance_type: str, operating_system: str, region: str,
              provider: str = "aws", pre_installed_sw: str = "NA",
              purchase_option: str = "on_demand") -> dict | None:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT provider, region, instance_type, operating_system, pre_installed_sw, license_model, purchase_option, price_per_hour_usd, effective_date FROM instance_price
               WHERE provider = %s AND region = %s AND instance_type = %s
                 AND operating_system = %s AND pre_installed_sw = %s AND purchase_option = %s""",
            (provider, region, instance_type, operating_system, pre_installed_sw, purchase_option),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def get_prices_for_region(region: str, provider: str = "aws") -> dict[tuple, dict]:
    """Bulk-load prices for a region into a lookup dict, keyed the same way tool_defs expects.
    Much cheaper than one query per candidate SKU during recommend_instances."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT provider, region, instance_type, operating_system, pre_installed_sw, license_model, purchase_option, price_per_hour_usd, effective_date FROM instance_price WHERE provider = %s AND region = %s "
            "AND pre_installed_sw = 'NA' AND purchase_option = 'on_demand'",
            (provider, region),
        )
        rows = [dict(r) for r in cur.fetchall()]
    return {(r["instance_type"], r["operating_system"]): r for r in rows}


def save_recommendation(workload_id: str, scenario: str, region: str, result: dict):
    top = result.get("top_choice")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO recommendation_run
               (workload_id, scenario, region, instance_type, monthly_cost,
                requirement, score_breakdown, binding_constraints)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                workload_id, scenario, region,
                top["instance_type"] if top else None,
                top["total_monthly"] if top else None,
                json.dumps(result.get("requirement")),
                json.dumps(top["score_breakdown"]) if top else None,
                json.dumps(result.get("binding_constraints")) if result.get("binding_constraints") else None,
            ),
        )
        conn.commit()
