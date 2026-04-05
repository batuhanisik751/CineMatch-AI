import { apiFetch } from "./client";
import type { DepScanResponse } from "./types";

export function getDepScanStatus() {
  return apiFetch<DepScanResponse>("/api/v1/system/dep-scan");
}
