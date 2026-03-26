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
