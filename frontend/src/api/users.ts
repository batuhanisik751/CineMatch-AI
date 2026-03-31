import { apiFetch } from "./client";
import type { CompletionsResponse, DiaryResponse, FeedResponse, TasteProfileResponse, UserResponse, UserStatsResponse } from "./types";

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

export function getUserFeed(userId: number, sections = 5) {
  return apiFetch<FeedResponse>(
    `/api/v1/users/${userId}/feed?sections=${sections}`
  );
}

export function getUserDiary(userId: number, year: number) {
  return apiFetch<DiaryResponse>(`/api/v1/users/${userId}/diary?year=${year}`);
}

export function getTasteProfile(userId: number) {
  return apiFetch<TasteProfileResponse>(
    `/api/v1/users/${userId}/taste-profile`
  );
}
