import { apiFetch } from "./client";
import type { OnboardingMoviesResponse, OnboardingStatusResponse } from "./types";

export function getOnboardingMovies(userId: number, count = 20) {
  return apiFetch<OnboardingMoviesResponse>(
    `/api/v1/onboarding/movies?user_id=${userId}&count=${count}`
  );
}

export function getOnboardingStatus(userId: number) {
  return apiFetch<OnboardingStatusResponse>(
    `/api/v1/onboarding/status?user_id=${userId}`
  );
}
