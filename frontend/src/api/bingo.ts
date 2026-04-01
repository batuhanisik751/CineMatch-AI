import { apiFetch } from "./client";
import type { BingoCardResponse } from "./types";

export function getUserBingo(userId: number, seed: string) {
  return apiFetch<BingoCardResponse>(
    `/api/v1/users/${userId}/bingo?seed=${seed}`
  );
}
