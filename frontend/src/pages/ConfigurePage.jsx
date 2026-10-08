import { useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight, Cloud, DollarSign, Scale, Gauge, Loader2 } from "lucide-react";
import { useApp } from "../context/AppContext";
import { getProviders, uploadAssessment, extractErrorMessage } from "../api/client";

const PROVIDER_OPTIONS = [
  { id: "aws", label: "AWS", sub: "Amazon Web Services" },
  { id: "azure", label: "Azure", sub: "Microsoft Azure" },
  { id: "both", label: "Both", sub: "Cross-cloud comparison" },
];

const SCENARIO_OPTIONS = [
  { id: "cost", label: "Cost Optimized", desc: "Tightest fit, highest utilization targets", icon: DollarSign },
  { id: "balanced", label: "Balanced", desc: "Sensible headroom across cost & performance", icon: Scale },
  { id: "performance", label: "Performance", desc: "Generous headroom, excludes burstable SKUs", icon: Gauge },
];

// The backend's /providers endpoint only returns a default region per provider, not a full list —
// so these are a curated set of common regions for the picker, with a free-text option alongside.
const COMMON_AWS_REGIONS = [
  "us-east-1", "us-east-2", "us-west-1", "us-west-2",
  "eu-west-1", "eu-west-2", "eu-central-1", "eu-north-1",
  "ap-south-1", "ap-southeast-1", "ap-southeast-2", "ap-northeast-1",
  "ca-central-1", "sa-east-1", "me-central-1", "me-south-1", "af-south-1",
];
const COMMON_AZURE_REGIONS = [
  "eastus", "eastus2", "westus", "westus2", "westus3",
  "northeurope", "westeurope", "uksouth", "ukwest",
  "centralindia", "southindia", "southeastasia", "eastasia",
  "australiaeast", "uaenorth", "brazilsouth",
];

export default function ConfigurePage() {
  const navigate = useNavigate();
  const { file, config, setConfig, setAssessment, setAssessError, isAssessing, setIsAssessing, assessError } = useApp();
  const [catalog, setCatalog] = useState(null);
  const [catalogError, setCatalogError] = useState(false);
  const [progress, setProgress] = useState(0);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [defaultsApplied, setDefaultsApplied] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!file) navigate("/upload");
  }, [file, navigate]);

  useEffect(() => {
    getProviders()
      .then((data) => setCatalog(data))
      .catch(() => setCatalogError(true));
  }, []);

  // Pre-fill regions from the backend's own defaults once, without clobbering anything the person typed.
  useEffect(() => {
    if (!catalog || defaultsApplied) return;
    const awsDefault = catalog?.aws?.default_region;
    const azureDefault = catalog?.azure?.default_region;
    setConfig((c) => ({
      ...c,
      awsRegion: awsDefault || c.awsRegion,
      azureRegion: azureDefault || c.azureRegion,
    }));
    setDefaultsApplied(true);
  }, [catalog, defaultsApplied, setConfig]);

  const toggleScenario = (id) => {
    setConfig((c) => {
      const has = c.scenarios.includes(id);
      const next = has ? c.scenarios.filter((s) => s !== id) : [...c.scenarios, id];
      return { ...c, scenarios: next.length ? next : c.scenarios };
    });
  };

  const canSubmit =
    file &&
    config.scenarios.length > 0 &&
    ((config.provider === "aws" && config.awsRegion) ||
      (config.provider === "azure" && config.azureRegion) ||
      (config.provider === "both" && config.awsRegion && config.azureRegion));

  const handleAssess = async () => {
    setIsAssessing(true);
    setAssessError(null);
    setProgress(0);
    setElapsedSec(0);
    timerRef.current = setInterval(() => setElapsedSec((s) => s + 1), 1000);
    try {
      const data = await uploadAssessment({
        file,
        provider: config.provider,
        awsRegion: config.provider !== "azure" ? config.awsRegion : undefined,
        azureRegion: config.provider !== "aws" ? config.azureRegion : undefined,
        scenarios: config.scenarios,
        groupName: config.groupName || undefined,
        onUploadProgress: (evt) => {
          if (evt.total) setProgress(Math.round((evt.loaded / evt.total) * 100));
        },
      });
      setAssessment(data);
      navigate("/results");
    } catch (err) {
      setAssessError(extractErrorMessage(err));
    } finally {
      clearInterval(timerRef.current);
      setIsAssessing(false);
    }
  };

  useEffect(() => () => clearInterval(timerRef.current), []);

  const formatElapsed = (s) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

  return (
    <div style={{ maxWidth: 920, margin: "0 auto", padding: "36px 0 80px" }}>
      <section style={{ marginBottom: 32 }}>
        <div className="eyebrow" style={{ marginBottom: 10 }}>
          Cloud provider
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
          {PROVIDER_OPTIONS.map((p) => {
            const active = config.provider === p.id;
            return (
              <div
                key={p.id}
                onClick={() => setConfig((c) => ({ ...c, provider: p.id }))}
                className="card"
                style={{
                  padding: "20px 18px",
                  cursor: "pointer",
                  borderColor: active ? "var(--accent-red)" : "var(--border-soft)",
                  background: active ? "var(--grad-card)" : "var(--surface-1)",
                  display: "flex",
                  alignItems: "center",
                  gap: 14,
                }}
              >
                <div
                  style={{
                    width: 40,
                    height: 40,
                    borderRadius: 12,
                    background: active ? "var(--grad-aurora)" : "var(--surface-3)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  <Cloud size={18} color={active ? "#ffffff" : "var(--text-secondary)"} />
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 15 }}>{p.label}</div>
                  <div style={{ fontSize: 12.5, color: "var(--text-muted)" }}>{p.sub}</div>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section style={{ marginBottom: 32 }}>
        <div className="eyebrow" style={{ marginBottom: 10 }}>
          Region
        </div>
        <div style={{ display: "grid", gridTemplateColumns: config.provider === "both" ? "1fr 1fr" : "1fr", gap: 14 }}>
          {(config.provider === "aws" || config.provider === "both") && (
            <div className="card" style={{ padding: 18 }}>
              <label style={{ fontSize: 12.5, color: "var(--text-muted)", display: "block", marginBottom: 8 }}>
                AWS region
              </label>
              <input
                className="input"
                list="aws-region-options"
                value={config.awsRegion}
                onChange={(e) => setConfig((c) => ({ ...c, awsRegion: e.target.value }))}
                placeholder="e.g. us-east-1"
              />
              <datalist id="aws-region-options">
                {COMMON_AWS_REGIONS.map((r) => (
                  <option key={r} value={r} />
                ))}
              </datalist>
            </div>
          )}
          {(config.provider === "azure" || config.provider === "both") && (
            <div className="card" style={{ padding: 18 }}>
              <label style={{ fontSize: 12.5, color: "var(--text-muted)", display: "block", marginBottom: 8 }}>
                Azure region
              </label>
              <input
                className="input"
                list="azure-region-options"
                value={config.azureRegion}
                onChange={(e) => setConfig((c) => ({ ...c, azureRegion: e.target.value }))}
                placeholder="e.g. eastus"
              />
              <datalist id="azure-region-options">
                {COMMON_AZURE_REGIONS.map((r) => (
                  <option key={r} value={r} />
                ))}
              </datalist>
            </div>
          )}
        </div>
        <p style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 10 }}>
          {catalogError
            ? "Couldn't reach the backend to pre-fill a default region — type one in directly."
            : "Pre-filled from your backend's default region. Pick from the list or type any other region code."}
        </p>
      </section>

      <section style={{ marginBottom: 32 }}>
        <div className="eyebrow" style={{ marginBottom: 10 }}>
          Scenarios
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
          {SCENARIO_OPTIONS.map(({ id, label, desc, icon: Icon }) => {
            const active = config.scenarios.includes(id);
            return (
              <div
                key={id}
                onClick={() => toggleScenario(id)}
                className="card"
                style={{
                  padding: 18,
                  cursor: "pointer",
                  borderColor: active ? "var(--accent-indigo)" : "var(--border-soft)",
                  background: active ? "var(--grad-card)" : "var(--surface-1)",
                }}
              >
                <Icon size={18} color={active ? "var(--accent-indigo)" : "var(--text-muted)"} />
                <div style={{ fontWeight: 600, fontSize: 14.5, marginTop: 10 }}>{label}</div>
                <div style={{ fontSize: 12.5, color: "var(--text-muted)", marginTop: 4, lineHeight: 1.5 }}>{desc}</div>
              </div>
            );
          })}
        </div>
      </section>

      <section style={{ marginBottom: 8 }}>
        <div className="eyebrow" style={{ marginBottom: 10 }}>
          Optional
        </div>
        <div className="card" style={{ padding: 18 }}>
          <label style={{ fontSize: 12.5, color: "var(--text-muted)", display: "block", marginBottom: 8 }}>
            Filter by group / environment name
          </label>
          <input
            className="input"
            placeholder="e.g. Production, Finance-DC1 (leave blank to assess all servers)"
            value={config.groupName}
            onChange={(e) => setConfig((c) => ({ ...c, groupName: e.target.value }))}
          />
        </div>
      </section>

      {assessError && (
        <div className="card" style={{ marginTop: 20, padding: "13px 16px", borderColor: "rgba(248,113,113,0.3)" }}>
          <span style={{ fontSize: 13.5, color: "var(--danger)" }}>{assessError}</span>
        </div>
      )}

      {isAssessing && (
        <div className="card" style={{ marginTop: 20, padding: "16px 18px", background: "var(--grad-card)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <Loader2 size={16} className="spin" color="var(--accent-red)" />
            <span style={{ fontWeight: 600, fontSize: 13.5 }}>
              {progress > 0 && progress < 100 ? `Uploading · ${progress}%` : "Sizing every server against live catalogs…"}
            </span>
            <span style={{ marginLeft: "auto", fontSize: 12.5, color: "var(--text-muted)" }}>
              {formatElapsed(elapsedSec)} elapsed
            </span>
          </div>
          <p style={{ fontSize: 12.5, color: "var(--text-muted)", lineHeight: 1.6, margin: 0 }}>
            A real fleet can take a few minutes — the backend is scoring every server against AWS/Azure
            pricing for each selected scenario. This page will move on automatically the moment it responds.
          </p>
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 32 }}>
        <button className="btn btn-ghost" onClick={() => navigate("/upload")} disabled={isAssessing}>
          <ArrowLeft size={16} />
          Back
        </button>
        <button className="btn btn-primary" disabled={!canSubmit || isAssessing} onClick={handleAssess}>
          {isAssessing ? (
            <>
              <Loader2 size={16} className="spin" />
              Running assessment…
            </>
          ) : (
            <>
              Run migration assessment
              <ArrowRight size={16} />
            </>
          )}
        </button>
      </div>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
