/**
 * API client for backend communication.
 * All fetch calls go through here — this is the boundary where we log.
 */

const API_BASE = "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  console.info(`[API] ${options?.method ?? "GET"} ${url}`);

  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    console.error(`[API] ${res.status} ${res.statusText} — ${url}`);
    throw new Error(`Request failed: ${res.status}`);
  }

  return res.json();
}

import type { HealthResponse, QueryResponse } from "./types";

export function healthcheck(): Promise<HealthResponse> {
  return request<HealthResponse>("/healthcheck/");
}

export function submitQuery(text: string): Promise<QueryResponse> {
  return request<QueryResponse>("/query/", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}
