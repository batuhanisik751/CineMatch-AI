import { apiFetch } from "./client";
import type {
  ChallengesCurrentResponse,
  ChallengesProgressResponse,
} from "./types";

export function getCurrentChallenges() {
  return apiFetch<ChallengesCurrentResponse>("/api/v1/challenges/current");
}

export function getChallengeProgress(userId: number) {
  return apiFetch<ChallengesProgressResponse>(
    `/api/v1/users/${userId}/challenges/progress`
  );
}
