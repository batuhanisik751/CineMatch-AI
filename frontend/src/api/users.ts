import { apiFetch } from "./client";
import type { UserResponse } from "./types";

export function getUser(id: number) {
  return apiFetch<UserResponse>(`/api/v1/users/${id}`);
}
