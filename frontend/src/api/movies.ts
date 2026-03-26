import { apiFetch } from "./client";
import type { MovieResponse, MovieSearchResponse, SimilarMoviesResponse } from "./types";

export function searchMovies(q: string, limit = 20) {
  return apiFetch<MovieSearchResponse>(
    `/api/v1/movies/search?q=${encodeURIComponent(q)}&limit=${limit}`
  );
}

export function getMovie(id: number) {
  return apiFetch<MovieResponse>(`/api/v1/movies/${id}`);
}

export function getSimilarMovies(id: number, topK = 20) {
  return apiFetch<SimilarMoviesResponse>(`/api/v1/movies/${id}/similar?top_k=${topK}`);
}
