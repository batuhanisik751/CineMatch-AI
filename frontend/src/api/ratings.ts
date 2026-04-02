import { ApiError, apiFetch } from "./client";
import type { ImportResponse, RatingResponse, UserRatingsResponse } from "./types";

const BASE_URL = "http://localhost:8000";

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

export async function importRatings(
  userId: number,
  file: File,
  source: "letterboxd" | "imdb" | "auto" = "auto"
): Promise<ImportResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(
    `${BASE_URL}/api/v1/users/${userId}/ratings/import?source=${source}`,
    { method: "POST", body: formData }
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(res.status, body.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function exportRatings(userId: number): Promise<void> {
  const res = await fetch(
    `${BASE_URL}/api/v1/users/${userId}/ratings/export`
  );
  if (!res.ok) throw new ApiError(res.status, "Export failed");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `cinematch_ratings_${userId}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}
