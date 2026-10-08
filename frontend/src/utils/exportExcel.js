import * as XLSX from "xlsx";

function scenarioCell(entry) {
  const empty = {
    provider: "", region: "", instance: "", family: "", vcpu: "", memory_gib: "",
    compute_monthly: "", total_monthly: "", os: "", processor: "", architecture: "",
    total_score: "", status: "",
  };
  if (!entry) return empty;
  const top = entry.top_choice;
  if (!top) {
    return { ...empty, status: "no_recommendation" };
  }
  return {
    provider: top.provider ?? "",
    region: top.region ?? "",
    instance: top.instance_type ?? "",
    family: top.family ?? "",
    vcpu: top.vcpu ?? "",
    memory_gib: top.memory_gib ?? "",
    compute_monthly: top.compute_monthly ?? "",
    total_monthly: top.total_monthly ?? "",
    os: top.os ?? "",
    processor: top.processor ?? "",
    architecture: top.architecture ?? "",
    total_score: top.total_score ?? "",
    status: entry.hardware_mapping ? "hardware_mapping (needs review)" : "ok",
  };
}

export function exportAssessmentToExcel(assessment, filename = "cloud-migration-plan.xlsx") {
  const wb = XLSX.utils.book_new();
  const scenarios = assessment.scenarios || [];
  const resultsRows = assessment.results || [];

  const summaryRows = resultsRows.map((row) => {
    const base = { workload_id: row.workload_id, server_name: row.server_name };
    scenarios.forEach((s) => {
      const cell = scenarioCell((row.scenarios || {})[s]);
      base[`${s}_provider`] = cell.provider;
      base[`${s}_region`] = cell.region;
      base[`${s}_instance_type`] = cell.instance;
      base[`${s}_vcpu`] = cell.vcpu;
      base[`${s}_memory_gib`] = cell.memory_gib;
      base[`${s}_total_monthly_usd`] = cell.total_monthly;
      base[`${s}_status`] = cell.status;
    });
    return base;
  });
  const summarySheet = XLSX.utils.json_to_sheet(summaryRows);
  XLSX.utils.book_append_sheet(wb, summarySheet, "Migration Plan");

  scenarios.forEach((s) => {
    const rows = resultsRows.map((row) => {
      const entry = (row.scenarios || {})[s];
      const cell = scenarioCell(entry);
      const req = entry?.requirement || {};
      return {
        workload_id: row.workload_id,
        server_name: row.server_name,
        provider: cell.provider,
        region: cell.region,
        instance_type: cell.instance,
        family: cell.family,
        vcpu: cell.vcpu,
        memory_gib: cell.memory_gib,
        processor: cell.processor,
        architecture: cell.architecture,
        os: cell.os,
        compute_monthly_usd: cell.compute_monthly,
        total_monthly_usd: cell.total_monthly,
        total_score: cell.total_score,
        status: cell.status,
        req_cpu_demand_cores: req.cpu_demand_cores ?? "",
        req_mem_gb: req.mem_gb ?? "",
        req_iops: req.iops ?? "",
        req_disk_mbps: req.disk_mbps ?? "",
        req_net_gbps: req.net_gbps ?? "",
        req_confidence: req.confidence ?? "",
        req_notes: (req.notes || []).join(" | "),
      };
    });
    const sheet = XLSX.utils.json_to_sheet(rows);
    XLSX.utils.book_append_sheet(wb, sheet, s.charAt(0).toUpperCase() + s.slice(1));
  });

  if (assessment.needs_review?.length) {
    const reviewSheet = XLSX.utils.json_to_sheet(assessment.needs_review);
    XLSX.utils.book_append_sheet(wb, reviewSheet, "Needs Review");
  } else {
    // Derive a "needs review" sheet ourselves when the backend's own list is empty but some
    // scenario still had no viable instance or only a hardware-mapping fallback.
    const derived = [];
    resultsRows.forEach((row) => {
      scenarios.forEach((s) => {
        const entry = (row.scenarios || {})[s];
        if (!entry?.top_choice) {
          derived.push({ workload_id: row.workload_id, server_name: row.server_name, scenario: s, reason: "no_recommendation" });
        } else if (entry.hardware_mapping) {
          derived.push({ workload_id: row.workload_id, server_name: row.server_name, scenario: s, reason: "hardware_mapping" });
        }
      });
    });
    if (derived.length) {
      const reviewSheet = XLSX.utils.json_to_sheet(derived);
      XLSX.utils.book_append_sheet(wb, reviewSheet, "Needs Review");
    }
  }

  XLSX.writeFile(wb, filename);
}
