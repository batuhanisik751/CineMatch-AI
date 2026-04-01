import { apiFetch } from "./client";
import type {
  PopularListsResponse,
  UserListDetailResponse,
  UserListItemResponse,
  UserListSummary,
  UserListsResponse,
} from "./types";

export function createList(
  userId: number,
  name: string,
  description?: string,
  isPublic = false,
) {
  return apiFetch<UserListSummary>(`/api/v1/users/${userId}/lists`, {
    method: "POST",
    body: JSON.stringify({ name, description: description || null, is_public: isPublic }),
  });
}

export function getUserLists(userId: number) {
  return apiFetch<UserListsResponse>(`/api/v1/users/${userId}/lists`);
}

export function getList(listId: number, offset = 0, limit = 40) {
  return apiFetch<UserListDetailResponse>(
    `/api/v1/lists/${listId}?offset=${offset}&limit=${limit}`,
  );
}

export function updateList(
  userId: number,
  listId: number,
  updates: { name?: string; description?: string; is_public?: boolean },
) {
  return apiFetch<UserListSummary>(`/api/v1/users/${userId}/lists/${listId}`, {
    method: "PATCH",
    body: JSON.stringify(updates),
  });
}

export function deleteList(userId: number, listId: number) {
  return apiFetch<void>(`/api/v1/users/${userId}/lists/${listId}`, {
    method: "DELETE",
  });
}

export function addMovieToList(userId: number, listId: number, movieId: number) {
  return apiFetch<UserListItemResponse>(
    `/api/v1/users/${userId}/lists/${listId}/items`,
    {
      method: "POST",
      body: JSON.stringify({ movie_id: movieId }),
    },
  );
}

export function removeMovieFromList(
  userId: number,
  listId: number,
  movieId: number,
) {
  return apiFetch<void>(
    `/api/v1/users/${userId}/lists/${listId}/items/${movieId}`,
    { method: "DELETE" },
  );
}

export function reorderListItems(
  userId: number,
  listId: number,
  movieIds: number[],
) {
  return apiFetch<{ status: string }>(
    `/api/v1/users/${userId}/lists/${listId}/items/reorder`,
    {
      method: "PUT",
      body: JSON.stringify({ movie_ids: movieIds }),
    },
  );
}

export function getPopularLists(offset = 0, limit = 20) {
  return apiFetch<PopularListsResponse>(
    `/api/v1/lists/popular?offset=${offset}&limit=${limit}`,
  );
}
