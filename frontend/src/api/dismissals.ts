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

const BULK_CHECK_LIMIT = 200;

export async function bulkCheckDismissals(
  userId: number,
  movieIds: number[]
): Promise<DismissalBulkStatusResponse> {
  if (movieIds.length <= BULK_CHECK_LIMIT) {
    return apiFetch<DismissalBulkStatusResponse>(
      `/api/v1/users/${userId}/dismissals/check?movie_ids=${movieIds.join(",")}`
    );
  }
  const allDismissed: number[] = [];
  for (let i = 0; i < movieIds.length; i += BULK_CHECK_LIMIT) {
    const batch = movieIds.slice(i, i + BULK_CHECK_LIMIT);
    const resp = await apiFetch<DismissalBulkStatusResponse>(
      `/api/v1/users/${userId}/dismissals/check?movie_ids=${batch.join(",")}`
    );
    allDismissed.push(...resp.movie_ids);
  }
  return { movie_ids: allDismissed };
}
