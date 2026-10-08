import { useLocation } from "react-router-dom";
import { HelpCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { getHealth } from "../api/client";

const TITLES = {
  "/upload": ["Step 1", "Upload on-prem infrastructure data"],
  "/configure": ["Step 2", "Select providers, regions & scenarios"],
  "/results": ["Step 3", "Migration recommendations"],
  "/chat": ["Step 4", "Ask the migration agent"],
};

export default function Topbar() {
  const location = useLocation();
  const [status, setStatus] = useState("checking");

  useEffect(() => {
    let mounted = true;
    getHealth()
      .then(() => mounted && setStatus("online"))
      .catch(() => mounted && setStatus("offline"));
    const interval = setInterval(() => {
      getHealth()
        .then(() => mounted && setStatus("online"))
        .catch(() => mounted && setStatus("offline"));
    }, 20000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  const [eyebrow, title] = TITLES[location.pathname] || ["", "Cloudinx"];

  return (
    <header
      style={{
        height: "var(--topbar-h)",
        position: "sticky",
        top: 0,
        zIndex: 10,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 32px",
        background: "var(--bg-topbar)",
        backdropFilter: "blur(14px)",
        borderBottom: "1px solid var(--border-soft)",
      }}
    >
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h2 style={{ fontSize: 19, fontWeight: 700 }}>{title}</h2>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
        <span
          className={`status-dot status-dot-${status}`}
          title={status === "online" ? "API connected" : status === "offline" ? "API unreachable" : "Checking connection…"}
        />

        <button className="btn btn-ghost btn-sm" title="Help">
          <HelpCircle size={15} />
          Help
        </button>

        <div
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            background: "var(--grad-indigo)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontWeight: 700,
            fontSize: 13,
          }}
        >
          SA
        </div>
      </div>
    </header>
  );
}
