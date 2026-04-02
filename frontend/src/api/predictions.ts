import { apiFetch } from "./client";
import type { PredictedMatchResponse } from "./types";

export function getPredictedMatch(
  userId: number,
  movieId: number
): Promise<PredictedMatchResponse> {
  return apiFetch(`/api/v1/users/${userId}/predicted-rating/${movieId}`);
}

export function getBatchPredictedMatches(
  userId: number,
  movieIds: number[]
): Promise<PredictedMatchResponse> {
  return apiFetch(`/api/v1/users/${userId}/predicted-ratings`, {
    method: "POST",
    body: JSON.stringify({ movie_ids: movieIds }),
  });
}
