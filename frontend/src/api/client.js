import axios from "axios";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
  // Sizing a real fleet against live AWS/Azure catalogs can take minutes — no hard timeout.
  timeout: 0,
});

export async function getHealth() {
  const { data } = await api.get("/health");
  return data;
}

export async function getProviders() {
  const { data } = await api.get("/providers");
  return data;
}

export async function uploadAssessment({ file, provider, awsRegion, azureRegion, scenarios, groupName, onUploadProgress }) {
  const form = new FormData();
  form.append("file", file);
  form.append("provider", provider);
  if (awsRegion) form.append("aws_region", awsRegion);
  if (azureRegion) form.append("azure_region", azureRegion);
  form.append("scenarios", scenarios.join(","));
  if (groupName) form.append("group_name", groupName);

  const { data } = await api.post("/assess/upload", form, {
    headers: { "Content-Type": "multipart/form-data" },
    onUploadProgress,
  });
  return data;
}

// NOTE: the backend's documented API surface (health / providers / assess/upload) didn't include
// an agent/chat endpoint. This assumes the conventional shape — POST /agent/chat with
// {message, history} — and parses the reply defensively from whichever key the real backend uses.
export async function sendChatMessage({ message, history }) {
  const { data } = await api.post("/agent/chat", { message, history });
  return { text: extractAgentReply(data), raw: data };
}

export function extractAgentReply(data) {
  if (data == null) return "";
  if (typeof data === "string") return data;
  const candidates = ["text", "response", "answer", "reply", "message", "output", "content"];
  for (const key of candidates) {
    if (typeof data[key] === "string" && data[key].trim()) return data[key];
  }
  // Some agent frameworks nest the final message, e.g. {message: {content: "..."}}
  if (data.message && typeof data.message === "object") {
    const nested = extractAgentReply(data.message);
    if (nested) return nested;
  }
  return JSON.stringify(data, null, 2);
}

export function extractErrorMessage(err) {
  if (err?.response?.data?.detail) return err.response.data.detail;
  if (err?.message) return err.message;
  return "Something went wrong. Please try again.";
}
