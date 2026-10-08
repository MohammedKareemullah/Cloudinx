"""
Strands @tool wrappers around the deterministic engine in tools/tool_defs.py.
Strands builds each tool's JSON schema from the type hints and the docstring (Args section),
so the docstrings below are what the model reads. Each tool returns a JSON string.
"""
import json
from strands import tool
from tools import tool_defs


def _json(obj) -> str:
    return json.dumps(obj, default=str)


@tool
def list_workloads(group_name: str = "") -> str:
    """List the on-premises servers available for assessment.

    Args:
        group_name: Optional vCenter/group name to filter by. Leave empty for all servers.
    """
    return _json(tool_defs.list_workloads(group_name or None))


@tool
def find_workloads_by_name(name_contains: str) -> str:
    """Find workload ids by (partial, case-insensitive) server name. Server names are not unique,
    so more than one match is possible.

    Args:
        name_contains: Part of the server name, e.g. "pwrds10".
    """
    items = tool_defs.list_workloads(None)["workloads"]
    matches = [w for w in items if name_contains.lower() in w["server_name"].lower()]
    return _json({"count": len(matches), "matches": matches[:25]})


@tool
def get_workload(workload_id: str) -> str:
    """Get the observed specs (vCPU, CPU %, memory, storage, IOPS, network, OS, SQL edition) of one server.

    Args:
        workload_id: The workload id, formatted "servername.UID".
    """
    return _json(tool_defs.get_workload(workload_id))


@tool
def get_requirements(workload_id: str, scenario: str) -> str:
    """Derive the raw cloud sizing demand (CPU demand in on-prem core-units, memory, IOPS, disk
    throughput, network, confidence, data-quality notes) for a server under one scenario. Note
    this is PRE-conversion demand, not a final vCPU count — the vCPU requirement depends on which
    cloud instance family it's being checked against (see recommend_instances / explain_score).

    Args:
        workload_id: The workload id, formatted "servername.UID".
        scenario: One of "cost", "balanced", "performance".
    """
    return _json(tool_defs.get_requirements(workload_id, scenario))


@tool
def search_instances(min_vcpu: int, min_mem_gb: float, provider: str = "aws", region: str = "",
                      min_iops: int = 0, min_disk_mbps: float = 0.0, min_net_gbps: float = 0.0) -> str:
    """Search the instance catalog for a cloud provider/region for instance types meeting minimum specs.

    Args:
        min_vcpu: Minimum vCPU count.
        min_mem_gb: Minimum memory in GiB.
        provider: "aws" or "azure". Defaults to "aws".
        region: Region code (AWS e.g. "us-east-1", Azure e.g. "eastus"). Empty uses that
            provider's configured default region.
        min_iops: Minimum max IOPS (0 = no filter).
        min_disk_mbps: Minimum max disk throughput in MB/s (0 = no filter).
        min_net_gbps: Minimum peak network bandwidth in Gbps (0 = no filter; Azure does not
            reliably publish this, so it has no effect for Azure).
    """
    return _json(tool_defs.search_instances(min_vcpu, min_mem_gb, provider, region,
                                             min_iops or None, min_disk_mbps or None, min_net_gbps or None))


@tool
def get_price(instance_type: str, os: str, provider: str = "aws", region: str = "") -> str:
    """Get the on-demand hourly/monthly price of one instance type from one provider.

    Args:
        instance_type: Instance type, e.g. "m7i.xlarge" (AWS) or "Standard_E8s_v5" (Azure).
        os: "linux" or "windows".
        provider: "aws" or "azure". Defaults to "aws".
        region: Region code. Empty uses that provider's configured default region.
    """
    return _json(tool_defs.get_price(instance_type, os, provider, region))


@tool
def recommend_instances(workload_id: str, provider: str = "aws", aws_region: str = "",
                         azure_region: str = "", scenarios: str = "cost,balanced,performance") -> str:
    """Run the full sizing, filtering, scoring and pricing pipeline for one server and return the
    top instance plus alternatives for each scenario. This is the main tool for producing a
    recommendation. To compare AWS and Azure head-to-head in one ranked list, set provider="both"
    and supply BOTH aws_region and azure_region.

    Args:
        workload_id: The workload id, formatted "servername.UID".
        provider: "aws", "azure", or "both". Defaults to "aws".
        aws_region: AWS region code, e.g. "us-east-1". Required if provider is "aws" or "both"
            (falls back to the configured default if left empty).
        azure_region: Azure region code, e.g. "eastus". Required if provider is "azure" or "both"
            (falls back to the configured default if left empty).
        scenarios: Comma-separated subset of "cost,balanced,performance".
    """
    wanted = [s.strip() for s in scenarios.split(",") if s.strip()]
    return _json(tool_defs.recommend_instances(workload_id, provider=provider, aws_region=aws_region,
                                                azure_region=azure_region, scenarios=wanted))


@tool
def explain_score(workload_id: str, instance_type: str, scenario: str, provider: str = "aws",
                   aws_region: str = "", azure_region: str = "") -> str:
    """Explain why an instance scored as it did for a server and scenario (cost/fit/perf/affinity
    breakdown), or why it's a hardware-mapping fallback. If the instance is not a candidate,
    returns the binding constraints instead.

    Args:
        workload_id: The workload id, formatted "servername.UID".
        instance_type: Instance type to explain.
        scenario: One of "cost", "balanced", "performance".
        provider: "aws", "azure", or "both" — must match how recommend_instances was called.
        aws_region: AWS region code, if relevant.
        azure_region: Azure region code, if relevant.
    """
    return _json(tool_defs.explain_score(workload_id, instance_type, scenario, provider,
                                          "", aws_region, azure_region))


ALL_TOOLS = [list_workloads, find_workloads_by_name, get_workload, get_requirements,
             search_instances, get_price, recommend_instances, explain_score]
