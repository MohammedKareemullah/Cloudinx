import { Fragment, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Download,
  Search,
  Server,
  DollarSign,
  AlertTriangle,
  MessageSquareText,
  ChevronDown,
  ChevronUp,
  Cpu,
  MemoryStick,
  Network,
  HardDrive,
} from "lucide-react";
import { useApp } from "../context/AppContext";
import { exportAssessmentToExcel } from "../utils/exportExcel";

const SCENARIO_LABELS = { cost: "Cost Optimized", balanced: "Balanced", performance: "Performance" };

// A scenario entry looks like: { requirement, top_choice, alternatives, hardware_mapping }
// top_choice (when present) looks like: { provider, region, instance_type, family, vcpu, memory_gib,
//   total_monthly, compute_monthly, os, processor, architecture, burstable, network_baseline_gbps,
//   network_peak_gbps, ebs_baseline_iops, ebs_max_iops, ebs_baseline_mbps, ebs_max_mbps,
//   instance_storage_gb, purchase_option, price_effective_date, score_breakdown, total_score }

function hasChoice(entry) {
  return !!entry?.top_choice;
}

function needsReview(entry) {
  if (!entry) return true;
  if (entry.hardware_mapping) return true;
  return !hasChoice(entry);
}

function StatusBadge({ entry }) {
  if (!entry) return <span className="badge badge-warn">no data</span>;
  if (!hasChoice(entry)) return <span className="badge badge-danger">no recommendation</span>;
  if (entry.hardware_mapping) return <span className="badge badge-warn">hardware mapping</span>;
  return <span className="badge badge-ok">recommended</span>;
}

function formatMoney(n) {
  if (n == null || Number.isNaN(n)) return "—";
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

function ScenarioCell({ entry }) {
  if (!entry) return <span style={{ color: "var(--text-muted)" }}>—</span>;
  const top = entry.top_choice;
  if (!top) {
    return <span style={{ fontSize: 12.5, color: "var(--danger)" }}>No viable instance found</span>;
  }
  return (
    <div>
      <div style={{ fontWeight: 600, fontSize: 13.5, display: "flex", alignItems: "center", gap: 6 }}>
        {top.instance_type || "—"}{" "}
        <span style={{ color: "var(--text-muted)", fontWeight: 400 }}>
          ({top.provider || "?"}{top.region ? ` · ${top.region}` : ""})
        </span>
        {entry.hardware_mapping && (
          <span className="badge badge-warn" style={{ fontSize: 10 }}>
            fallback
          </span>
        )}
      </div>
      <div style={{ fontSize: 12, color: "var(--text-muted)", display: "flex", gap: 10, marginTop: 3, flexWrap: "wrap" }}>
        <span>
          <Cpu size={10} style={{ marginRight: 3, verticalAlign: -1 }} />
          {top.vcpu ?? "—"} vCPU
        </span>
        <span>
          <MemoryStick size={10} style={{ marginRight: 3, verticalAlign: -1 }} />
          {top.memory_gib ?? "—"} GiB
        </span>
        <span style={{ color: "var(--accent-red)" }}>
          {top.total_monthly != null ? `${formatMoney(top.total_monthly)}/mo` : "— /mo"}
        </span>
      </div>
    </div>
  );
}

export default function ResultsPage() {
  const navigate = useNavigate();
  const { assessment } = useApp();
  const [search, setSearch] = useState("");
  const [expandedRow, setExpandedRow] = useState(null);
  const [filter, setFilter] = useState("all");

  useEffect(() => {
    if (!assessment) navigate("/upload");
  }, [assessment, navigate]);

  const scenarios = assessment?.scenarios || [];

  const stats = useMemo(() => {
    if (!assessment) return null;
    const totals = {};
    scenarios.forEach((s) => (totals[s] = 0));
    let reviewCount = 0;
    const rows = assessment.results || [];
    rows.forEach((row) => {
      const rowScenarios = row?.scenarios || {};
      scenarios.forEach((s) => {
        const entry = rowScenarios[s];
        if (hasChoice(entry) && !entry.hardware_mapping) {
          totals[s] += entry.top_choice.total_monthly || 0;
        } else {
          reviewCount += 1;
        }
      });
    });
    return { totals, reviewCount, serverCount: assessment.workload_count ?? rows.length };
  }, [assessment, scenarios]);

  const filteredRows = useMemo(() => {
    if (!assessment) return [];
    let rows = assessment.results || [];
    if (search.trim()) {
      const q = search.toLowerCase();
      rows = rows.filter(
        (r) => (r.server_name || "").toLowerCase().includes(q) || (r.workload_id || "").toLowerCase().includes(q)
      );
    }
    if (filter === "review") {
      rows = rows.filter((r) => scenarios.some((s) => needsReview((r.scenarios || {})[s])));
    }
    return rows;
  }, [assessment, search, filter, scenarios]);

  if (!assessment || !stats) return null;

  if (!assessment.results?.length) {
    return (
      <div style={{ maxWidth: 560, margin: "80px auto", textAlign: "center" }}>
        <h3 style={{ fontSize: 18, marginBottom: 8 }}>No results to show</h3>
        <p style={{ color: "var(--text-muted)", fontSize: 14, marginBottom: 20 }}>
          The assessment came back empty. Try uploading the spreadsheet again.
        </p>
        <button className="btn btn-primary" onClick={() => navigate("/upload")}>
          Back to upload
        </button>
      </div>
    );
  }

  return (
    <div style={{ padding: "36px 0 80px" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${Math.min(scenarios.length + 2, 4)}, 1fr)`,
          gap: 16,
          marginBottom: 28,
        }}
      >
        <div className="card" style={{ padding: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 10,
                background: "var(--surface-3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Server size={16} color="var(--accent-red)" />
            </div>
            <span className="eyebrow">Servers assessed</span>
          </div>
          <div style={{ fontSize: 28, fontWeight: 800, fontFamily: "var(--font-display)" }}>{stats.serverCount}</div>
        </div>

        {scenarios.map((s) => (
          <div key={s} className="card" style={{ padding: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
              <div
                style={{
                  width: 34,
                  height: 34,
                  borderRadius: 10,
                  background: "var(--surface-3)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <DollarSign size={16} color="var(--accent-red)" />
              </div>
              <span className="eyebrow">{SCENARIO_LABELS[s] || s}</span>
            </div>
            <div style={{ fontSize: 28, fontWeight: 800, fontFamily: "var(--font-display)" }}>
              {formatMoney(stats.totals[s])}
            </div>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>per month, on-demand</div>
          </div>
        ))}

        <div
          className="card"
          style={{ padding: 20, borderColor: stats.reviewCount ? "rgba(251,191,36,0.3)" : "var(--border-soft)" }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 10,
                background: "var(--surface-3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <AlertTriangle size={16} color="var(--warning)" />
            </div>
            <span className="eyebrow">Needs review</span>
          </div>
          <div style={{ fontSize: 28, fontWeight: 800, fontFamily: "var(--font-display)" }}>{stats.reviewCount}</div>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16, gap: 12 }}>
        <div style={{ display: "flex", gap: 10, flex: 1 }}>
          <div style={{ position: "relative", maxWidth: 320, flex: 1 }}>
            <Search size={15} style={{ position: "absolute", left: 13, top: 12, color: "var(--text-muted)" }} />
            <input
              className="input"
              style={{ paddingLeft: 36 }}
              placeholder="Search server name or ID…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <button className="btn btn-sm btn-ghost" style={{ opacity: filter === "all" ? 1 : 0.6 }} onClick={() => setFilter("all")}>
              All
            </button>
            <button className="btn btn-sm btn-ghost" style={{ opacity: filter === "review" ? 1 : 0.6 }} onClick={() => setFilter("review")}>
              Needs review ({stats.reviewCount})
            </button>
          </div>
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          <button className="btn btn-ghost" onClick={() => navigate("/chat")}>
            <MessageSquareText size={16} />
            Ask the agent
          </button>
          <button className="btn btn-accent" onClick={() => exportAssessmentToExcel(assessment)}>
            <Download size={16} />
            Export to Excel
          </button>
        </div>
      </div>

      <div className="card" style={{ overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr style={{ background: "var(--surface-2)" }}>
              <th style={thStyle}>Server</th>
              {scenarios.map((s) => (
                <th style={thStyle} key={s}>
                  {SCENARIO_LABELS[s] || s}
                </th>
              ))}
              <th style={{ ...thStyle, width: 40 }}></th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row) => {
              const isOpen = expandedRow === row.workload_id;
              const rowScenarios = row.scenarios || {};
              return (
                <Fragment key={row.workload_id}>
                  <tr
                    style={{ borderTop: "1px solid var(--border-soft)", cursor: "pointer" }}
                    onClick={() => setExpandedRow(isOpen ? null : row.workload_id)}
                  >
                    <td style={tdStyle}>
                      <div style={{ fontWeight: 600, fontSize: 13.5 }}>{row.server_name || row.workload_id}</div>
                      <div style={{ fontSize: 11.5, color: "var(--text-muted)" }}>{row.workload_id}</div>
                    </td>
                    {scenarios.map((s) => (
                      <td style={tdStyle} key={s}>
                        <ScenarioCell entry={rowScenarios[s]} />
                      </td>
                    ))}
                    <td style={tdStyle}>{isOpen ? <ChevronUp size={15} /> : <ChevronDown size={15} />}</td>
                  </tr>
                  {isOpen && (
                    <tr style={{ background: "var(--surface-1)" }}>
                      <td colSpan={scenarios.length + 2} style={{ padding: "18px 20px", borderTop: "1px solid var(--border-soft)" }}>
                        <div
                          style={{
                            display: "grid",
                            gridTemplateColumns: `repeat(${Math.min(scenarios.length, 3)}, 1fr)`,
                            gap: 18,
                          }}
                        >
                          {scenarios.map((s) => {
                            const entry = rowScenarios[s];
                            const top = entry?.top_choice;
                            const req = entry?.requirement;
                            const alts = entry?.alternatives || [];
                            return (
                              <div key={s}>
                                <div
                                  className="eyebrow"
                                  style={{ marginBottom: 8, display: "flex", alignItems: "center", gap: 8 }}
                                >
                                  {SCENARIO_LABELS[s] || s}
                                  <StatusBadge entry={entry} />
                                </div>

                                {req && (
                                  <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.7, marginBottom: 10 }}>
                                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
                                      <span>
                                        <Cpu size={11} style={{ marginRight: 3, verticalAlign: -1 }} />
                                        {req.cpu_demand_cores ?? "—"} cores demand
                                      </span>
                                      <span>
                                        <MemoryStick size={11} style={{ marginRight: 3, verticalAlign: -1 }} />
                                        {req.mem_gb ?? "—"} GB
                                      </span>
                                    </div>
                                    <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 2 }}>
                                      <span>
                                        <HardDrive size={11} style={{ marginRight: 3, verticalAlign: -1 }} />
                                        {req.iops ?? "—"} IOPS · {req.disk_mbps ?? "—"} Mbps
                                      </span>
                                      <span>
                                        <Network size={11} style={{ marginRight: 3, verticalAlign: -1 }} />
                                        {req.net_gbps ?? "—"} Gbps
                                      </span>
                                    </div>
                                    {req.confidence && (
                                      <div style={{ marginTop: 4 }}>
                                        Confidence: <span style={{ color: "var(--warning)" }}>{req.confidence}</span>
                                      </div>
                                    )}
                                    {req.notes?.length > 0 && (
                                      <ul style={{ margin: "6px 0 0", paddingLeft: 16, color: "var(--text-muted)" }}>
                                        {req.notes.map((n, i) => (
                                          <li key={i} style={{ marginBottom: 2 }}>
                                            {n}
                                          </li>
                                        ))}
                                      </ul>
                                    )}
                                  </div>
                                )}

                                {top ? (
                                  <div
                                    style={{
                                      background: "var(--surface-2)",
                                      border: "1px solid var(--border-soft)",
                                      borderRadius: "var(--radius-sm)",
                                      padding: 12,
                                      fontSize: 12,
                                      color: "var(--text-secondary)",
                                      lineHeight: 1.7,
                                    }}
                                  >
                                    <div style={{ fontWeight: 600, color: "var(--text-primary)", marginBottom: 4 }}>
                                      {top.instance_type} <span style={{ color: "var(--text-muted)" }}>({top.family})</span>
                                    </div>
                                    <div>
                                      {top.processor || "—"} · {top.architecture || "—"} · {top.os || "—"}
                                      {top.burstable ? " · burstable" : ""}
                                    </div>
                                    <div>
                                      Network: {top.network_baseline_gbps ?? "—"}–{top.network_peak_gbps ?? "—"} Gbps
                                    </div>
                                    <div>
                                      EBS: {top.ebs_baseline_iops ?? "—"}–{top.ebs_max_iops ?? "—"} IOPS ·{" "}
                                      {top.ebs_baseline_mbps ?? "—"}–{top.ebs_max_mbps ?? "—"} Mbps
                                    </div>
                                    {top.instance_storage_gb != null && <div>Instance storage: {top.instance_storage_gb} GB</div>}
                                    <div>
                                      Compute: {formatMoney(top.compute_monthly)}/mo · Total: {formatMoney(top.total_monthly)}/mo
                                    </div>
                                    {top.score_breakdown && (
                                      <div style={{ marginTop: 4 }}>
                                        Score — cost {top.score_breakdown.cost ?? "—"} · fit {top.score_breakdown.fit ?? "—"} ·
                                        perf {top.score_breakdown.perf ?? "—"} · affinity {top.score_breakdown.affinity ?? "—"}{" "}
                                        <strong>(total {top.total_score ?? "—"})</strong>
                                      </div>
                                    )}
                                    {top.price_effective_date && (
                                      <div style={{ color: "var(--text-muted)", marginTop: 2 }}>
                                        Price as of {top.price_effective_date}
                                      </div>
                                    )}
                                  </div>
                                ) : (
                                  <div style={{ fontSize: 12.5, color: "var(--danger)" }}>
                                    No instance in the catalog satisfied this workload's requirements for this scenario.
                                  </div>
                                )}

                                {alts.length > 0 && (
                                  <div style={{ marginTop: 10 }}>
                                    <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>
                                      Alternatives
                                    </div>
                                    {alts.slice(0, 3).map((a, i) => (
                                      <div
                                        key={i}
                                        style={{
                                          display: "flex",
                                          justifyContent: "space-between",
                                          fontSize: 12,
                                          color: "var(--text-secondary)",
                                          padding: "4px 0",
                                          borderTop: i === 0 ? "none" : "1px solid var(--border-soft)",
                                        }}
                                      >
                                        <span>{a.instance_type}</span>
                                        <span>
                                          {formatMoney(a.total_monthly)}/mo · score {a.total_score ?? "—"}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>

      <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 16, lineHeight: 1.6 }}>
        Prices are on-demand, compute-only estimates for the selected region. Storage, licensing (e.g. SQL Server
        edition-based licensing), data transfer, and HA/DR architecture are not included — review those separately
        before finalizing a migration cost.
      </p>
    </div>
  );
}

const thStyle = {
  textAlign: "left",
  padding: "12px 20px",
  fontSize: 11.5,
  fontWeight: 600,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
  color: "var(--text-muted)",
};
const tdStyle = { padding: "14px 20px", verticalAlign: "top" };
