import { apiFetch } from "./client";
import type {
  MoodRecommendationResponse,
  RecommendationExplanation,
  RecommendationsResponse,
  SurpriseResponse,
} from "./types";

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

export function getMoodRecommendations(params: {
  mood: string;
  user_id: number;
  alpha?: number;
  limit?: number;
}) {
  return apiFetch<MoodRecommendationResponse>("/api/v1/recommendations/mood", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function getSurpriseMovies(userId: number, limit = 5) {
  return apiFetch<SurpriseResponse>(
    `/api/v1/users/${userId}/surprise?limit=${limit}`
  );
}
