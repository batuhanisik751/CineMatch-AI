import { apiFetch } from "./client";
import type { DbSecurityStatusResponse } from "./types";

export function getDbSecurityStatus() {
  return apiFetch<DbSecurityStatusResponse>("/api/v1/system/db-security");
}
