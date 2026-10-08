"""
Aggregates recommend_instances() across every workload into a fleet-wide migration plan:
per-server line items plus a summary (cost by scenario, family mix, confidence, and every
workload that needed a hardware-mapping fallback or hit a data gap — these need human review
before the plan is final, they are not silently swept into the numbers).
"""
from dataclasses import dataclass, field
from db import repository as repo
from tools.tool_defs import recommend_instances


@dataclass
class PlanSummary:
    total_workloads: int = 0
    scenario_totals: dict = field(default_factory=dict)   # scenario -> total monthly $
    family_counts: dict = field(default_factory=dict)     # scenario -> {family: count}
    hardware_mapping_count: dict = field(default_factory=dict)  # scenario -> count
    low_confidence_count: int = 0
    empty_catalog_count: int = 0
    needs_review: list = field(default_factory=list)      # (workload_id, server_name, scenario, reason)


def build_plan(region: str, group_name: str | None = None,
               scenarios: list[str] | None = None) -> dict:
    scenarios = scenarios or ["cost", "balanced", "performance"]
    workloads = repo.list_workloads(group_name)
    summary = PlanSummary(total_workloads=len(workloads))
    for s in scenarios:
        summary.scenario_totals[s] = 0.0
        summary.family_counts[s] = {}
        summary.hardware_mapping_count[s] = 0

    line_items = []
    for w in workloads:
        result = recommend_instances(w["id"], region=region, scenarios=scenarios, persist=True)

        if "error" in result:
            summary.empty_catalog_count += 1
            summary.needs_review.append((w["id"], w["server_name"], "*", result["error"]))
            continue

        for scenario in scenarios:
            scen = result["scenarios"].get(scenario, {})
            req = scen.get("requirement", {})
            if req.get("confidence") == "low":
                summary.low_confidence_count += 1

            top = scen.get("top_choice")
            if not top:
                summary.needs_review.append((w["id"], w["server_name"], scenario,
                                              scen.get("error", "no_candidates")))
                continue

            summary.scenario_totals[scenario] += top["total_monthly"]
            fam = top["family"]
            summary.family_counts[scenario][fam] = summary.family_counts[scenario].get(fam, 0) + 1

            if scen.get("hardware_mapping"):
                summary.hardware_mapping_count[scenario] += 1
                summary.needs_review.append((w["id"], w["server_name"], scenario,
                                              "hardware_mapping: " + scen.get("diagnosis", "")))

            line_items.append({
                "workload_id": w["id"], "server_name": w["server_name"], "scenario": scenario,
                "instance_type": top["instance_type"], "vcpu": top["vcpu"], "memory_gib": top["memory_gib"],
                "monthly_cost": top["total_monthly"], "hardware_mapping": scen.get("hardware_mapping", False),
                "confidence": req.get("confidence"), "notes": "; ".join(req.get("notes", [])),
            })

    return {"summary": summary, "line_items": line_items, "region": region, "scenarios": scenarios}


def print_plan(plan: dict):
    s = plan["summary"]
    print(f"\n=== Migration plan — {s.total_workloads} workloads, region {plan['region']} ===\n")
    for scenario in plan["scenarios"]:
        print(f"[{scenario}] total monthly compute cost: ${s.scenario_totals[scenario]:,.2f}")
        fams = sorted(s.family_counts[scenario].items(), key=lambda x: -x[1])
        print(f"  family mix: {', '.join(f'{f}={c}' for f, c in fams)}")
        if s.hardware_mapping_count[scenario]:
            print(f"  hardware-mapping fallbacks (need manual review): {s.hardware_mapping_count[scenario]}")
        print()
    print(f"Low-confidence sizings (single point-in-time CPU reading): {s.low_confidence_count}")
    print(f"Workloads with no usable catalog (region not ingested?): {s.empty_catalog_count}")
    if s.needs_review:
        print(f"\n{len(s.needs_review)} items flagged for manual review:")
        for wid, name, scenario, reason in s.needs_review[:20]:
            print(f"  {name:20s} [{scenario:11s}] {reason}")
        if len(s.needs_review) > 20:
            print(f"  ... and {len(s.needs_review) - 20} more")
