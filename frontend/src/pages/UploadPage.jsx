import { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadCloud, FileSpreadsheet, CheckCircle2, X, ArrowRight, Info } from "lucide-react";
import * as XLSX from "xlsx";
import { useApp } from "../context/AppContext";

export default function UploadPage() {
  const navigate = useNavigate();
  const { file, setFile, fileMeta, setFileMeta, resetAssessment } = useApp();
  const [dragOver, setDragOver] = useState(false);
  const [parsing, setParsing] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const handleFile = useCallback(
    async (selected) => {
      if (!selected) return;
      const validExt = /\.(xlsx|xls)$/i.test(selected.name);
      if (!validExt) {
        setError("Please upload a .xlsx or .xls file exported from your infrastructure discovery tool.");
        return;
      }
      setError(null);
      setParsing(true);
      resetAssessment();
      try {
        const buf = await selected.arrayBuffer();
        const wb = XLSX.read(buf, { type: "array" });
        const sheetNames = wb.SheetNames;
        let computeRowCount = 0;
        if (sheetNames.includes("Compute")) {
          const sheet = wb.Sheets["Compute"];
          const rows = XLSX.utils.sheet_to_json(sheet, { header: 1, range: 1 });
          computeRowCount = rows.filter((r) => r && r.length).length;
        }
        setFile(selected);
        setFileMeta({
          name: selected.name,
          size: selected.size,
          sheetNames,
          workloadCount: computeRowCount || null,
        });
      } catch (e) {
        setError("Could not read that spreadsheet. Make sure it's a valid Excel export with Compute/Storage/Network sheets.");
      } finally {
        setParsing(false);
      }
    },
    [setFile, setFileMeta, resetAssessment]
  );

  const onDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files?.[0];
    handleFile(dropped);
  };

  const clearFile = () => {
    setFile(null);
    setFileMeta(null);
    resetAssessment();
    if (inputRef.current) inputRef.current.value = "";
  };

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "36px 0 80px" }}>
      <div style={{ marginBottom: 28 }}>
        <p style={{ color: "var(--text-secondary)", fontSize: 15, lineHeight: 1.6, maxWidth: 620 }}>
          Upload your on-prem infrastructure discovery export (Compute, Storage and Network sheets — the standard
          Azure Migrate-style format). We'll size every server against live AWS and Azure catalogs and recommend the
          right instance for cost, balanced, and performance scenarios.
        </p>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        className="card"
        style={{
          padding: 48,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          borderStyle: dragOver ? "solid" : "dashed",
          borderColor: dragOver ? "var(--accent-red)" : "var(--border-soft)",
          background: dragOver ? "rgba(239,68,68,0.05)" : "var(--surface-1)",
          transition: "all 0.15s ease",
          cursor: "pointer",
        }}
        onClick={() => !file && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls"
          style={{ display: "none" }}
          onChange={(e) => handleFile(e.target.files?.[0])}
        />

        {!file ? (
          <>
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: 18,
                background: "var(--grad-card)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: 18,
              }}
            >
              <UploadCloud size={28} color="var(--accent-red)" />
            </div>
            <h3 style={{ fontSize: 18, marginBottom: 6 }}>
              {parsing ? "Reading spreadsheet…" : "Drop your spreadsheet here"}
            </h3>
            <p style={{ color: "var(--text-muted)", fontSize: 13.5, marginBottom: 20 }}>
              or click to browse · .xlsx / .xls · up to ~50MB
            </p>
            <button className="btn btn-accent" disabled={parsing} onClick={(e) => e.stopPropagation()}>
              <FileSpreadsheet size={16} />
              Browse files
            </button>
          </>
        ) : (
          <div style={{ width: "100%", display: "flex", alignItems: "center", gap: 16, textAlign: "left" }}>
            <div
              style={{
                width: 52,
                height: 52,
                borderRadius: 14,
                background: "rgba(52,211,153,0.12)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <CheckCircle2 size={24} color="var(--success)" />
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 15, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {fileMeta?.name}
              </div>
              <div style={{ fontSize: 13, color: "var(--text-muted)", marginTop: 2 }}>
                {(fileMeta?.size / 1024).toFixed(0)} KB
                {fileMeta?.workloadCount ? ` · ${fileMeta.workloadCount} servers detected` : ""}
                {fileMeta?.sheetNames ? ` · sheets: ${fileMeta.sheetNames.join(", ")}` : ""}
              </div>
            </div>
            <button
              className="btn btn-ghost btn-sm"
              onClick={(e) => {
                e.stopPropagation();
                clearFile();
              }}
            >
              <X size={14} />
              Remove
            </button>
          </div>
        )}
      </div>

      {error && (
        <div
          className="card"
          style={{ marginTop: 16, padding: "13px 16px", display: "flex", gap: 10, borderColor: "rgba(248,113,113,0.3)" }}
        >
          <Info size={16} color="var(--danger)" style={{ flexShrink: 0, marginTop: 1 }} />
          <span style={{ fontSize: 13.5, color: "var(--text-secondary)" }}>{error}</span>
        </div>
      )}

      <div
        className="card"
        style={{ marginTop: 24, padding: 20, display: "flex", gap: 14, background: "var(--grad-card)" }}
      >
        <Info size={18} color="var(--accent-red)" style={{ flexShrink: 0, marginTop: 1 }} />
        <div style={{ fontSize: 13.5, color: "var(--text-secondary)", lineHeight: 1.6 }}>
          <strong style={{ color: "var(--text-primary)" }}>Expected format:</strong> a workbook with{" "}
          <code style={{ color: "var(--accent-red)" }}>Compute</code>,{" "}
          <code style={{ color: "var(--accent-red)" }}>Storage</code>, and{" "}
          <code style={{ color: "var(--accent-red)" }}>Network</code> sheets, each keyed by a server UID — the
          standard output of Azure Migrate / Cloudamize-style discovery tools. We parse CPU utilization, memory, disk
          IOPS/throughput, and network demand directly from these sheets; nothing is estimated from scratch.
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 32 }}>
        <button className="btn btn-primary" disabled={!file || parsing} onClick={() => navigate("/configure")}>
          Continue to configuration
          <ArrowRight size={16} />
        </button>
      </div>
    </div>
  );
}
