import pandas as pd
import json

DAYS_PER_MONTH = 30
SECONDS_PER_DAY = 86400

def _extract_uid(id_str: str, sheet: str) -> str:
    parts = id_str.split(".")
    if sheet == "storage":
        return parts[0]
    return parts[-1] if len(parts) > 1 else parts[0]

def _read_sheet(path: str, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name=sheet_name, header=1, engine="openpyxl")
    df.columns = [str(c).strip() for c in df.columns]
    return df

def load_compute(path: str) -> pd.DataFrame:
    df = _read_sheet(path, "Compute")
    df["uid"] = df["ID (server name + uid)"].apply(lambda x: _extract_uid(str(x), "compute"))
    return df

def load_storage(path: str) -> pd.DataFrame:
    df = _read_sheet(path, "Storage")
    df["uid"] = df["ID (server name + uid)"].apply(lambda x: _extract_uid(str(x), "storage"))
    agg = df.groupby("uid").agg(
        storage_gb=("Observed Disk Capacity (GB)", "sum"),
        storage_used_gb=("Observed Disk Occupancy (GB)", "sum"),
        iops_peak=("Peak IOPS", "sum"),
        disk_throughput_mbps=("Observed Throughput (MBps)", "sum"),
        disk_count=("Disk", "count"),
    ).reset_index()
    agg["disk_throughput_mbps"] = agg["disk_throughput_mbps"] * 8
    return agg

def load_network(path: str) -> pd.DataFrame:
    df = _read_sheet(path, "Network")
    df["uid"] = df["ID (server name + uid)"].apply(lambda x: _extract_uid(str(x), "network"))
    total_gb_month = df["GB/month leaving server"] + df["GB/month from other Servers/Devices"]
    avg_mbps = (total_gb_month * 8 * 1024) / (DAYS_PER_MONTH * SECONDS_PER_DAY)
    peak_mbps = avg_mbps * (1 + df["Predicted Peak (%)"].fillna(0))
    return pd.DataFrame({"uid": df["uid"], "net_avg_mbps": avg_mbps, "net_mbps_peak": peak_mbps})

def normalize_os(raw: str) -> str:
    return "windows" if "windows" in str(raw).lower() else "linux"

def _clean(v):
    """Convert pandas NaN/NaT/'-' placeholders to None so psycopg2 can bind them."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(v, str) and v.strip() in ("", "-"):
        return None
    return v

def _num(v, cast=float):
    v = _clean(v)
    return cast(v) if v is not None else None

def build_workloads(path: str) -> list[dict]:
    compute = load_compute(path)
    storage = load_storage(path)
    network = load_network(path)
    merged = compute.merge(storage, on="uid", how="left").merge(network, on="uid", how="left")

    rows = []
    for _, r in merged.iterrows():
        rows.append({
            "id": str(r["ID (server name + uid)"]),
            "group_name": _clean(r.get("Group Name")),
            "asset": _clean(r.get("Asset")),
            "server_name": str(r["Server Name"]),
            "ip_address": _clean(r.get("IP Address")),
            "os": normalize_os(r["OS"]),
            "os_version": _clean(r.get("OS Version")),
            "sql_edition": _clean(r.get("MS SQL Edition")),
            "sql_version": _clean(r.get("SQL Version")),
            "on_time_pct": _num(r.get("On Time (%)")),
            "observed_vcpu": int(r["Observed vCPU"]),
            "cpu_util_pct": float(r["Current CPU Utilization (%)"]),
            "cpu_confidence": "point_in_time",
            "mem_provisioned_gb": float(r["Observed Memory Provisioned (GB)"]),
            "mem_peak_gb": _num(r.get("Peak Memory Used (GB)")),
            "storage_gb": _num(r.get("storage_gb")),
            "iops_peak": _num(r.get("iops_peak"), int),
            "disk_throughput_mbps": _num(r.get("disk_throughput_mbps")),
            "net_mbps_peak": _num(r.get("net_mbps_peak")),
            "net_confidence": "derived",
        })
    return rows

if __name__ == "__main__":
    import sys
    rows = build_workloads(sys.argv[1])
    print(f"Parsed {len(rows)} workloads")
    for r in rows[:3]:
        print(json.dumps(r, indent=2, default=str))
