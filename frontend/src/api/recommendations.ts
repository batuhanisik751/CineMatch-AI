import { apiFetch } from "./client";
import type { RecommendationsResponse } from "./types";

export function getRecommendations(userId: number, topK = 20, strategy = "hybrid") {
  return apiFetch<RecommendationsResponse>(
    `/api/v1/users/${userId}/recommendations?top_k=${topK}&strategy=${strategy}`
  );
}
