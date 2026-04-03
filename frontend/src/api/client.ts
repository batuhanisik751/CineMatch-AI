import { API_BASE_URL } from "../config";

const TOKEN_KEY = "cinematch_auth_token";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string
  ) {
    super(detail);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...Object.fromEntries(
      Object.entries(init?.headers || {}).filter(([, v]) => v != null) as [string, string][]
    ),
  };

  // Add auth token if present
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
  });

  if (!res.ok) {
    // On 401, dispatch event so AuthProvider can logout via React state
    if (res.status === 401) {
      window.dispatchEvent(new Event("auth:logout"));
    }

    // On 429, dispatch event for toast notification
    if (res.status === 429) {
      const retryAfter = res.headers.get("Retry-After");
      const seconds = retryAfter ? parseInt(retryAfter, 10) : 60;
      const body = await res.json().catch(() => ({ detail: "Too many requests" }));
      const message =
        body.detail || `Too many requests. Please wait ${seconds} seconds.`;
      window.dispatchEvent(
        new CustomEvent("rate-limited", {
          detail: { message, retryAfter: seconds },
        })
      );
      throw new ApiError(429, message);
    }

    const body = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}
