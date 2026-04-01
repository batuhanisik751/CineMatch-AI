import { apiFetch } from "./client";
import type { GlobalStatsResponse } from "./types";

export function getGlobalStats() {
  return apiFetch<GlobalStatsResponse>("/api/v1/stats/global");
}
