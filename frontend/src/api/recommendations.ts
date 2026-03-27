import { apiFetch } from "./client";
import type { RecommendationExplanation, RecommendationsResponse } from "./types";

export function getRecommendations(userId: number, topK = 20, strategy = "hybrid") {
  return apiFetch<RecommendationsResponse>(
    `/api/v1/users/${userId}/recommendations?top_k=${topK}&strategy=${strategy}`
  );
}

export function getExplanation(userId: number, movieId: number, score: number) {
  return apiFetch<RecommendationExplanation>(
    `/api/v1/users/${userId}/recommendations/explain/${movieId}?score=${score}`
  );
}
