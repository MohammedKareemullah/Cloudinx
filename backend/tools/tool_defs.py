"""
Tool schemas + dispatch functions for the migration assessment agent.
Reads workloads/catalog/prices from Postgres via db/repository.py — deterministic
engine code, never the LLM, produces every number.

Multi-provider: recommend_instances takes a list of {"provider", "region"} targets and
scores candidates from ALL of them together, so AWS and Azure compete head-to-head in one
ranked list per scenario. Each target's catalog is lazily ingested on first use.
"""

from db import repository as repo
from config.settings import DEFAULT_ASSESSMENT_REGION, DEFAULT_AZURE_REGION, DEFAULT_PROVIDER
from engine.sizing import derive_requirements, SCENARIO_CONFIG
from engine.selection import passes_hard_filters, score_candidates, shortfall_score
from engine.pricing import monthly_cost
from engine.catalog_ensure import ensure_catalog


def _default_targets() -> list[dict]:
    if DEFAULT_PROVIDER == "azure":
        return [{"provider": "azure", "region": DEFAULT_AZURE_REGION}]
    return [{"provider": "aws", "region": DEFAULT_ASSESSMENT_REGION}]


def _normalize_targets(provider: str, region: str, aws_region: str, azure_region: str) -> list[dict]:
    """Builds the target list from whichever combination of args was given. Supports three
    shapes: a single provider+region, a single provider using its default region, or both
    providers at once (pass aws_region and azure_region together) for a cross-cloud comparison."""
    if aws_region and azure_region:
        return [{"provider": "aws", "region": aws_region}, {"provider": "azure", "region": azure_region}]
    if provider == "both":
        return [{"provider": "aws", "region": aws_region or DEFAULT_ASSESSMENT_REGION},
                {"provider": "azure", "region": azure_region or DEFAULT_AZURE_REGION}]
    if provider == "azure" or azure_region:
        return [{"provider": "azure", "region": azure_region or region or DEFAULT_AZURE_REGION}]
    if provider == "aws" or aws_region or region:
        return [{"provider": "aws", "region": aws_region or region or DEFAULT_ASSESSMENT_REGION}]
    return _default_targets()


def list_workloads(group_name: str | None = None) -> dict:
    items = repo.list_workloads(group_name)
    return {"count": len(items), "workloads": items}


def get_workload(workload_id: str) -> dict:
    wl = repo.get_workload(workload_id)
    return wl if wl else {"error": "not_found", "workload_id": workload_id}


def get_requirements(workload_id: str, scenario: str) -> dict:
    wl = repo.get_workload(workload_id)
    if not wl:
        return {"error": "not_found", "workload_id": workload_id}
    if scenario not in SCENARIO_CONFIG:
        return {"error": "invalid_scenario", "valid": list(SCENARIO_CONFIG)}
    req = derive_requirements(wl, scenario)
    return {"workload_id": workload_id, "scenario": scenario, **req.__dict__}


def search_instances(min_vcpu: int, min_mem_gb: float, provider: str = "aws", region: str = "",
                      min_iops: int | None = None, min_disk_mbps: float | None = None,
                      min_net_gbps: float | None = None, os: str = "linux") -> dict:
    region = region or (DEFAULT_AZURE_REGION if provider == "azure" else DEFAULT_ASSESSMENT_REGION)
    ensure_catalog(provider, region)
    results = repo.search_instances(region, min_vcpu, min_mem_gb, min_iops, min_disk_mbps,
                                     min_net_gbps, provider=provider)
    return {"count": len(results), "provider": provider, "region": region, "instances": results[:25]}


def get_price(instance_type: str, os: str, provider: str = "aws", region: str = "") -> dict:
    region = region or (DEFAULT_AZURE_REGION if provider == "azure" else DEFAULT_ASSESSMENT_REGION)
    ensure_catalog(provider, region)
    os_label = "Windows" if os == "windows" else "Linux"
    price = repo.get_price(instance_type, os_label, region, provider=provider)
    return price if price else {"error": "price_not_found", "instance_type": instance_type, "os": os}


def recommend_instances(workload_id: str, provider: str = "", region: str = "",
                         aws_region: str = "", azure_region: str = "",
                         scenarios: list[str] | None = None, persist: bool = True) -> dict:
    wl = repo.get_workload(workload_id)
    if not wl:
        return {"error": "not_found", "workload_id": workload_id}

    targets = _normalize_targets(provider, region, aws_region, azure_region)
    for t in targets:
        try:
            ensure_catalog(t["provider"], t["region"])
        except Exception as e:
            return {"error": "ingestion_failed", "target": t, "detail": str(e)}

    catalog, prices = [], {}
    for t in targets:
        cat = repo.get_catalog(t["region"], provider=t["provider"])
        if not cat:
            return {"error": "empty_catalog_for_region", "target": t,
                    "hint": f"No instance data for {t['provider']}/{t['region']} even after "
                            "attempting ingestion — check credentials and that the region name is valid."}
        catalog.extend(cat)
        prices.update({(k[0], k[1], t["provider"]): v
                        for k, v in repo.get_prices_for_region(t["region"], provider=t["provider"]).items()})

    os_label = "Windows" if wl["os"] == "windows" else "Linux"
    scenarios = scenarios or list(SCENARIO_CONFIG)
    out = {}
    for scenario in scenarios:
        req = derive_requirements(wl, scenario)
        notes = list(req.notes)
        non_aws_families = {c["family"] for c in catalog if c["provider"] != "aws"}
        if non_aws_families:
            notes.append("CPU performance ratio table was calibrated from AWS data only — "
                          "non-AWS families use the fallback default ratio, which is an "
                          "approximation until a matching reference dataset is available.")

        candidates, priced_out, rejects = [], [], {}
        for sku in catalog:
            ok, reason, req_vcpu = passes_hard_filters(sku, req, wl, scenario)
            if not ok:
                rejects[reason] = rejects.get(reason, 0) + 1
                continue
            price = prices.get((sku["instance_type"], os_label, sku["provider"]))
            if not price:
                priced_out.append((sku["provider"], sku["instance_type"]))
                continue
            cand = {**sku, **monthly_cost(sku, price)}
            cand["_req_vcpu"] = req_vcpu
            candidates.append(cand)

        if priced_out:
            rejects["missing_price"] = len(priced_out)

        if candidates:
            ranked = score_candidates(candidates, req, wl, scenario)
            result = {"requirement": {**req.__dict__, "notes": notes}, "top_choice": ranked[0],
                      "alternatives": ranked[1:3], "hardware_mapping": False}
        elif priced_out and not any(k != "missing_price" for k in rejects):
            result = {"error": "no_candidates", "binding_constraints": rejects,
                      "requirement": {**req.__dict__, "notes": notes},
                      "diagnosis": "Every catalog SKU that fit spec-wise has no price on file "
                                   "for this OS/region — a price-ingestion gap, not a genuine "
                                   "sizing failure."}
        else:
            priced_candidates = []
            for sku in catalog:
                price = prices.get((sku["instance_type"], os_label, sku["provider"]))
                if price:
                    priced_candidates.append({**sku, **monthly_cost(sku, price)})
            if priced_candidates:
                best = min(priced_candidates, key=lambda s: shortfall_score(s, req, wl, scenario))
                result = {"requirement": {**req.__dict__, "notes": notes}, "top_choice": best,
                          "alternatives": [], "hardware_mapping": True, "binding_constraints": rejects,
                          "diagnosis": "No instance across the requested target(s) fully meets the "
                                       "sizing requirement. This is the closest available match "
                                       "(hardware mapping) — review manually before using it."}
            else:
                result = {"error": "no_candidates", "binding_constraints": rejects,
                          "requirement": {**req.__dict__, "notes": notes}}

        out[scenario] = result
        if persist:
            repo.save_recommendation(workload_id, scenario, "/".join(f"{t['provider']}:{t['region']}" for t in targets), result)

    return {"workload_id": workload_id, "targets": targets, "scenarios": out}


def explain_score(workload_id: str, instance_type: str, scenario: str,
                   provider: str = "", region: str = "", aws_region: str = "", azure_region: str = "") -> dict:
    result = recommend_instances(workload_id, provider, region, aws_region, azure_region,
                                  [scenario], persist=False)
    scen = result.get("scenarios", {}).get(scenario, {})
    for cand in [scen.get("top_choice")] + scen.get("alternatives", []):
        if cand and cand.get("instance_type") == instance_type:
            if scen.get("hardware_mapping"):
                return {"instance_type": instance_type, "scenario": scenario, "hardware_mapping": True,
                        "monthly_cost": cand["total_monthly"], "diagnosis": scen.get("diagnosis")}
            return {"instance_type": instance_type, "scenario": scenario,
                    "score_breakdown": cand["score_breakdown"], "total_score": cand["total_score"],
                    "monthly_cost": cand["total_monthly"]}
    return {"error": "instance_not_in_candidate_set", "possible_reason": scen.get("binding_constraints")}
