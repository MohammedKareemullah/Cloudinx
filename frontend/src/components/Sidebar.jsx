import { NavLink } from "react-router-dom";
import { UploadCloud, SlidersHorizontal, Table2, MessageSquareText, Cloud, ChevronRight } from "lucide-react";
import { useApp } from "../context/AppContext";

const STEPS = [
  { to: "/upload", label: "Upload", icon: UploadCloud, step: 1 },
  { to: "/configure", label: "Configure", icon: SlidersHorizontal, step: 2 },
  { to: "/results", label: "Results", icon: Table2, step: 3 },
  { to: "/chat", label: "Ask the Agent", icon: MessageSquareText, step: 4 },
];

export default function Sidebar() {
  const { assessment, fileMeta } = useApp();

  const isStepUnlocked = (step) => {
    if (step <= 2) return true;
    if (step === 3) return !!assessment;
    if (step === 4) return !!assessment;
    return false;
  };

  return (
    <aside
      style={{
        width: "var(--sidebar-w)",
        background: "var(--bg-sidebar)",
        borderRight: "1px solid var(--border-soft)",
        display: "flex",
        flexDirection: "column",
        position: "fixed",
        top: 0,
        bottom: 0,
        left: 0,
        padding: "22px 16px",
        zIndex: 20,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, padding: "0 8px 28px" }}>
        <div
          style={{
            width: 34,
            height: 34,
            borderRadius: 10,
            background: "var(--grad-aurora)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            flexShrink: 0,
          }}
        >
          <Cloud size={18} color="#ffffff" strokeWidth={2.4} />
        </div>
        <div style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 18, letterSpacing: "-0.01em" }}>
          Cloudinx
        </div>
      </div>

      <div className="eyebrow" style={{ padding: "0 8px 10px" }}>
        Assessment Flow
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {STEPS.map(({ to, label, icon: Icon, step }) => {
          const unlocked = isStepUnlocked(step);
          return (
            <NavLink
              key={to}
              to={unlocked ? to : "#"}
              onClick={(e) => !unlocked && e.preventDefault()}
              style={({ isActive }) => ({
                display: "flex",
                alignItems: "center",
                gap: 11,
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                fontSize: 14,
                fontWeight: 500,
                color: !unlocked ? "var(--text-muted)" : isActive ? "var(--text-primary)" : "var(--text-secondary)",
                background: isActive ? "var(--surface-2)" : "transparent",
                border: isActive ? "1px solid var(--border-soft)" : "1px solid transparent",
                cursor: unlocked ? "pointer" : "not-allowed",
                opacity: unlocked ? 1 : 0.5,
              })}
            >
              <span
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 22,
                  height: 22,
                  borderRadius: 7,
                  background: "var(--surface-3)",
                  fontSize: 11,
                  fontWeight: 700,
                  color: "var(--text-secondary)",
                  flexShrink: 0,
                }}
              >
                {step}
              </span>
              <Icon size={16} style={{ flexShrink: 0 }} />
              <span style={{ flex: 1 }}>{label}</span>
              <ChevronRight size={14} style={{ opacity: 0.4 }} />
            </NavLink>
          );
        })}
      </nav>

      <div style={{ flex: 1 }} />

      {fileMeta && (
        <div
          className="card"
          style={{
            padding: 14,
            background: "var(--grad-card)",
            display: "flex",
            flexDirection: "column",
            gap: 6,
          }}
        >
          <div className="eyebrow">Loaded dataset</div>
          <div style={{ fontSize: 13, fontWeight: 600, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {fileMeta.name}
          </div>
          <div style={{ fontSize: 12, color: "var(--text-muted)" }}>
            {fileMeta.workloadCount != null ? `${fileMeta.workloadCount} servers` : `${(fileMeta.size / 1024).toFixed(0)} KB`}
          </div>
        </div>
      )}
    </aside>
  );
}
