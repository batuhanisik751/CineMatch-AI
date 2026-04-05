import { apiFetch } from "./client";
import type { ContainerSecurityResponse } from "./types";

export function getContainerSecurityStatus() {
  return apiFetch<ContainerSecurityResponse>("/api/v1/system/container-security");
}
