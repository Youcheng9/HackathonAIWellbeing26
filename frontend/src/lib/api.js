import { API_BASE } from "./constants";

export async function analyzeScheduleRequest(payload) {
  const response = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const rawBody = await response.text();
  let parsedBody = null;
  if (rawBody) {
    try {
      parsedBody = JSON.parse(rawBody);
    } catch {
      parsedBody = null;
    }
  }

  if (!response.ok) {
    const detail = parsedBody?.detail;
    const normalizedDetail = Array.isArray(detail)
      ? detail.map((entry) => entry?.msg || JSON.stringify(entry)).join(", ")
      : detail;
    const message =
      normalizedDetail ||
      parsedBody?.message ||
      `Unable to analyze schedule. Backend returned ${response.status}.`;
    throw new Error(message);
  }

  if (!parsedBody) {
    throw new Error("Backend returned an empty response.");
  }

  return parsedBody;
}
