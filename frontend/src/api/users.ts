import { apiFetch } from "./client";
import type { CompletionsResponse, UserResponse, UserStatsResponse } from "./types";

export function getUser(id: number) {
  return apiFetch<UserResponse>(`/api/v1/users/${id}`);
}

export function getUserStats(id: number) {
  return apiFetch<UserStatsResponse>(`/api/v1/users/${id}/stats`);
}

export function getCompletions(userId: number, limit = 10) {
  return apiFetch<CompletionsResponse>(
    `/api/v1/users/${userId}/completions?limit=${limit}`
  );
}
