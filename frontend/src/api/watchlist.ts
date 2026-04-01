import { apiFetch } from "./client";
import type {
  RecommendationsResponse,
  WatchlistItemResponse,
  WatchlistResponse,
  WatchlistBulkStatusResponse,
} from "./types";

export function addToWatchlist(userId: number, movieId: number) {
  return apiFetch<WatchlistItemResponse>(`/api/v1/users/${userId}/watchlist`, {
    method: "POST",
    body: JSON.stringify({ movie_id: movieId }),
  });
}

export function removeFromWatchlist(userId: number, movieId: number) {
  return apiFetch<void>(`/api/v1/users/${userId}/watchlist/${movieId}`, {
    method: "DELETE",
  });
}

export function getWatchlist(userId: number, offset = 0, limit = 20) {
  return apiFetch<WatchlistResponse>(
    `/api/v1/users/${userId}/watchlist?offset=${offset}&limit=${limit}`
  );
}

export function bulkCheckWatchlist(userId: number, movieIds: number[]) {
  return apiFetch<WatchlistBulkStatusResponse>(
    `/api/v1/users/${userId}/watchlist/check?movie_ids=${movieIds.join(",")}`
  );
}

export function getWatchlistRecommendations(userId: number, limit = 10) {
  return apiFetch<RecommendationsResponse>(
    `/api/v1/users/${userId}/watchlist/recommendations?limit=${limit}`
  );
}
