import { apiFetch } from "./client";
import type { PickleSafetyResponse } from "./types";

export function getPickleSafetyStatus() {
  return apiFetch<PickleSafetyResponse>("/api/v1/system/pickle-safety");
}
