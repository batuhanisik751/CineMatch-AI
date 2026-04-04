import { apiFetch } from "./client";
import type { AuditLogListResponse } from "./types";

export interface AuditLogFilters {
  action?: string;
  status?: string;
  from_date?: string;
  to_date?: string;
  offset?: number;
  limit?: number;
}

export function getAuditLogs(filters: AuditLogFilters = {}) {
  const params = new URLSearchParams();
  if (filters.action) params.set("action", filters.action);
  if (filters.status) params.set("status", filters.status);
  if (filters.from_date) params.set("from_date", filters.from_date);
  if (filters.to_date) params.set("to_date", filters.to_date);
  params.set("offset", String(filters.offset ?? 0));
  params.set("limit", String(filters.limit ?? 50));
  return apiFetch<AuditLogListResponse>(`/api/v1/users/audit-logs?${params}`);
}
