import { apiFetch } from "./client";
import type { UserResponse, UserStatsResponse } from "./types";

export function getUser(id: number) {
  return apiFetch<UserResponse>(`/api/v1/users/${id}`);
}

export function getUserStats(id: number) {
  return apiFetch<UserStatsResponse>(`/api/v1/users/${id}/stats`);
}
