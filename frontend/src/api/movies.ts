import { apiFetch } from "./client";
import type {
  GenresResponse,
  MovieListResponse,
  MovieResponse,
  MovieSearchResponse,
  SemanticSearchResponse,
  SimilarMoviesResponse,
} from "./types";

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

export function discoverMovies(params: {
  genre?: string;
  year_min?: number;
  year_max?: number;
  sort_by?: string;
  offset?: number;
  limit?: number;
}) {
  const qs = new URLSearchParams();
  if (params.genre) qs.set("genre", params.genre);
  if (params.year_min != null) qs.set("year_min", String(params.year_min));
  if (params.year_max != null) qs.set("year_max", String(params.year_max));
  if (params.sort_by) qs.set("sort_by", params.sort_by);
  if (params.offset != null) qs.set("offset", String(params.offset));
  if (params.limit != null) qs.set("limit", String(params.limit));
  return apiFetch<MovieListResponse>(`/api/v1/movies/discover?${qs.toString()}`);
}

export function semanticSearchMovies(q: string, limit = 20) {
  return apiFetch<SemanticSearchResponse>(
    `/api/v1/movies/semantic-search?q=${encodeURIComponent(q)}&limit=${limit}`
  );
}

export function getGenres() {
  return apiFetch<GenresResponse>("/api/v1/movies/genres");
}
