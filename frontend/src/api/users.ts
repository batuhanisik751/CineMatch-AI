import { apiFetch } from "./client";
import type { AffinitiesResponse, CompletionsResponse, DiaryResponse, FeedResponse, RatingComparisonResponse, StreakResponse, TasteEvolutionResponse, TasteProfileResponse, UserResponse, UserStatsResponse } from "./types";

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

export function getRatingComparison(userId: number) {
  return apiFetch<RatingComparisonResponse>(
    `/api/v1/users/${userId}/rating-comparison`
  );
}

export function getUserAffinities(userId: number, limit = 15) {
  return apiFetch<AffinitiesResponse>(
    `/api/v1/users/${userId}/affinities?limit=${limit}`
  );
}

export function getTasteProfile(userId: number) {
  return apiFetch<TasteProfileResponse>(
    `/api/v1/users/${userId}/taste-profile`
  );
}

export function getUserStreaks(userId: number) {
  return apiFetch<StreakResponse>(`/api/v1/users/${userId}/streaks`);
}

export function getUserTasteEvolution(userId: number, granularity = "quarter") {
  return apiFetch<TasteEvolutionResponse>(
    `/api/v1/users/${userId}/taste-evolution?granularity=${granularity}`
  );
}
