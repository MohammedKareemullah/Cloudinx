import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Send, Sparkles, Loader2, Bot, User, AlertCircle } from "lucide-react";
import { useApp } from "../context/AppContext";
import { sendChatMessage, extractErrorMessage } from "../api/client";

const SUGGESTIONS = [
  "Which servers need manual review and why?",
  "What's the total monthly cost for the balanced scenario?",
  "Which server has the biggest cost difference between AWS and Azure?",
  "Explain why a specific instance was recommended for a server.",
];

export default function ChatPage() {
  const navigate = useNavigate();
  const { assessment, chatHistory, setChatHistory } = useApp();
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    if (!assessment) navigate("/upload");
  }, [assessment, navigate]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory, sending]);

  const handleSend = async (text) => {
    const message = (text ?? input).trim();
    if (!message || sending) return;
    setError(null);
    setInput("");
    const nextHistory = [...chatHistory, { role: "user", content: message }];
    setChatHistory(nextHistory);
    setSending(true);
    try {
      const { text: reply } = await sendChatMessage({ message, history: nextHistory });
      setChatHistory([...nextHistory, { role: "assistant", content: reply }]);
    } catch (err) {
      if (err?.response?.status === 404) {
        setError(
          "The agent endpoint (POST /agent/chat) isn't available on this backend yet. Once it's wired up, this page will work without any frontend changes."
        );
      } else {
        setError(extractErrorMessage(err));
      }
      setChatHistory(nextHistory);
    } finally {
      setSending(false);
    }
  };

  if (!assessment) return null;

  return (
    <div style={{ maxWidth: 860, margin: "0 auto", padding: "28px 0 24px", display: "flex", flexDirection: "column", height: "calc(100vh - var(--topbar-h) - 52px)" }}>
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          paddingBottom: 20,
          display: "flex",
          flexDirection: "column",
          gap: 18,
        }}
      >
        {chatHistory.length === 0 && (
          <div style={{ textAlign: "center", padding: "60px 20px" }}>
            <div
              style={{
                width: 64,
                height: 64,
                borderRadius: "50%",
                background: "var(--grad-aurora)",
                margin: "0 auto 20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Sparkles size={26} color="#ffffff" />
            </div>
            <h3 style={{ fontSize: 20, marginBottom: 8 }}>Ask about your migration plan</h3>
            <p style={{ color: "var(--text-muted)", fontSize: 14, maxWidth: 440, margin: "0 auto 24px", lineHeight: 1.6 }}>
              The agent has full access to your {assessment.workload_count}-server assessment — sizing requirements,
              recommended instances, costs, and anything flagged for manual review.
            </p>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
              {SUGGESTIONS.map((s) => (
                <button key={s} className="pill" style={{ cursor: "pointer" }} onClick={() => handleSend(s)}>
                  {s}
                </button>
              ))}
            </div>
            <p style={{ fontSize: 11.5, color: "var(--text-muted)", marginTop: 22 }}>
              Talks to <code style={{ color: "var(--text-secondary)" }}>POST /agent/chat</code> on your backend.
            </p>
          </div>
        )}

        {chatHistory.map((msg, i) => (
          <div key={i} style={{ display: "flex", gap: 12, alignItems: "flex-start", flexDirection: msg.role === "user" ? "row-reverse" : "row" }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                background: msg.role === "user" ? "var(--grad-indigo)" : "var(--surface-3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              {msg.role === "user" ? <User size={15} /> : <Bot size={15} color="var(--accent-red)" />}
            </div>
            <div
              className="card"
              style={{
                padding: "12px 16px",
                maxWidth: "78%",
                background: msg.role === "user" ? "var(--surface-2)" : "var(--surface-1)",
                fontSize: 14,
                lineHeight: 1.65,
                whiteSpace: "pre-wrap",
              }}
            >
              {msg.content}
            </div>
          </div>
        ))}

        {sending && (
          <div style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                background: "var(--surface-3)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
              }}
            >
              <Bot size={15} color="var(--accent-red)" />
            </div>
            <div className="card" style={{ padding: "12px 16px", display: "flex", alignItems: "center", gap: 8, fontSize: 13.5, color: "var(--text-muted)" }}>
              <Loader2 size={14} className="spin" />
              Thinking…
            </div>
          </div>
        )}

        {error && (
          <div className="card" style={{ padding: "12px 16px", display: "flex", gap: 10, borderColor: "rgba(248,113,113,0.3)" }}>
            <AlertCircle size={16} color="var(--danger)" style={{ flexShrink: 0, marginTop: 1 }} />
            <span style={{ fontSize: 13.5, color: "var(--text-secondary)" }}>{error}</span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      <div
        className="card"
        style={{
          padding: 10,
          display: "flex",
          alignItems: "center",
          gap: 10,
          borderRadius: "var(--radius-pill)",
        }}
      >
        <Sparkles size={16} color="var(--accent-red)" style={{ marginLeft: 8, flexShrink: 0 }} />
        <input
          className="input"
          style={{ border: "none", background: "transparent", flex: 1 }}
          placeholder="Ask about sizing, cost, or any server in the assessment…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          disabled={sending}
        />
        <button
          className="btn btn-accent btn-sm"
          style={{ borderRadius: "50%", width: 38, height: 38, padding: 0 }}
          onClick={() => handleSend()}
          disabled={sending || !input.trim()}
        >
          <Send size={15} />
        </button>
      </div>

      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
