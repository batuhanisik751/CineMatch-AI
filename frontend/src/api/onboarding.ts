import { apiFetch } from "./client";
import type { OnboardingMoviesResponse, OnboardingStatusResponse } from "./types";

export function getOnboardingMovies(_userId: number, count = 20) {
  return apiFetch<OnboardingMoviesResponse>(
    `/api/v1/onboarding/movies?count=${count}`
  );
}

export function getOnboardingStatus(_userId: number) {
  return apiFetch<OnboardingStatusResponse>(
    `/api/v1/onboarding/status`
  );
}
