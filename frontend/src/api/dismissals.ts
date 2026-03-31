import { apiFetch } from "./client";
import type { DismissalResponse, DismissalListResponse, DismissalBulkStatusResponse } from "./types";

export function dismissMovie(userId: number, movieId: number) {
  return apiFetch<DismissalResponse>(`/api/v1/users/${userId}/dismissals`, {
    method: "POST",
    body: JSON.stringify({ movie_id: movieId }),
  });
}

export function undismissMovie(userId: number, movieId: number) {
  return apiFetch<void>(`/api/v1/users/${userId}/dismissals/${movieId}`, {
    method: "DELETE",
  });
}

export function getDismissals(userId: number, offset = 0, limit = 20) {
  return apiFetch<DismissalListResponse>(
    `/api/v1/users/${userId}/dismissals?offset=${offset}&limit=${limit}`
  );
}

export function bulkCheckDismissals(userId: number, movieIds: number[]) {
  return apiFetch<DismissalBulkStatusResponse>(
    `/api/v1/users/${userId}/dismissals/check?movie_ids=${movieIds.join(",")}`
  );
}
