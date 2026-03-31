import { apiFetch } from "./client";
import type { RatingResponse, UserRatingsResponse } from "./types";

export function addRating(userId: number, movieId: number, rating: number) {
  return apiFetch<RatingResponse>(`/api/v1/users/${userId}/ratings`, {
    method: "POST",
    body: JSON.stringify({ movie_id: movieId, rating }),
  });
}

export function getUserRatings(userId: number, offset = 0, limit = 20) {
  return apiFetch<UserRatingsResponse>(
    `/api/v1/users/${userId}/ratings?offset=${offset}&limit=${limit}`
  );
}

export interface RatingBulkCheckResponse {
  ratings: Record<number, number>;
}

export function bulkCheckRatings(userId: number, movieIds: number[]) {
  return apiFetch<RatingBulkCheckResponse>(
    `/api/v1/users/${userId}/ratings/check?movie_ids=${movieIds.join(",")}`
  );
}
