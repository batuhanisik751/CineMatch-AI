import { apiFetch } from "./client";
import type {
  ActorFilmographyResponse,
  ActorSearchResponse,
  DecadeMoviesResponse,
  DecadesResponse,
  DirectorFilmographyResponse,
  DirectorSearchResponse,
  GenresResponse,
  HiddenGemsResponse,
  KeywordMoviesResponse,
  KeywordSearchResponse,
  MovieListResponse,
  MovieResponse,
  MovieSearchResponse,
  PopularActorsResponse,
  PopularDirectorsResponse,
  PopularKeywordsResponse,
  SemanticSearchResponse,
  SimilarMoviesResponse,
  TopChartsResponse,
  TrendingResponse,
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

export function getTrendingMovies(window = 7, limit = 20) {
  return apiFetch<TrendingResponse>(
    `/api/v1/movies/trending?window=${window}&limit=${limit}`
  );
}

export function getTopCharts(genre: string, limit = 20) {
  return apiFetch<TopChartsResponse>(
    `/api/v1/movies/top?genre=${encodeURIComponent(genre)}&limit=${limit}`
  );
}

export function getHiddenGems(params: {
  min_rating?: number;
  max_votes?: number;
  genre?: string;
  limit?: number;
} = {}) {
  const qs = new URLSearchParams();
  if (params.min_rating != null) qs.set("min_rating", String(params.min_rating));
  if (params.max_votes != null) qs.set("max_votes", String(params.max_votes));
  if (params.genre) qs.set("genre", params.genre);
  if (params.limit != null) qs.set("limit", String(params.limit));
  return apiFetch<HiddenGemsResponse>(`/api/v1/movies/hidden-gems?${qs.toString()}`);
}

export function getDecades() {
  return apiFetch<DecadesResponse>("/api/v1/movies/decades");
}

export function getDecadeMovies(decade: number, params: {
  genre?: string;
  offset?: number;
  limit?: number;
} = {}) {
  const qs = new URLSearchParams();
  if (params.genre) qs.set("genre", params.genre);
  if (params.offset != null) qs.set("offset", String(params.offset));
  if (params.limit != null) qs.set("limit", String(params.limit));
  const query = qs.toString();
  return apiFetch<DecadeMoviesResponse>(
    `/api/v1/movies/decades/${decade}${query ? `?${query}` : ""}`
  );
}

export function searchDirectors(q: string, limit = 20) {
  return apiFetch<DirectorSearchResponse>(
    `/api/v1/movies/directors/search?q=${encodeURIComponent(q)}&limit=${limit}`
  );
}

export function getPopularDirectors(limit = 30) {
  return apiFetch<PopularDirectorsResponse>(
    `/api/v1/movies/directors/popular?limit=${limit}`
  );
}

export function getDirectorFilmography(name: string, userId?: number) {
  const qs = new URLSearchParams({ name });
  if (userId != null) qs.set("user_id", String(userId));
  return apiFetch<DirectorFilmographyResponse>(
    `/api/v1/movies/directors/filmography?${qs.toString()}`
  );
}

export function searchActors(q: string, limit = 20) {
  return apiFetch<ActorSearchResponse>(
    `/api/v1/movies/actors/search?q=${encodeURIComponent(q)}&limit=${limit}`
  );
}

export function getPopularActors(limit = 30) {
  return apiFetch<PopularActorsResponse>(
    `/api/v1/movies/actors/popular?limit=${limit}`
  );
}

export function getActorFilmography(name: string, userId?: number) {
  const qs = new URLSearchParams({ name });
  if (userId != null) qs.set("user_id", String(userId));
  return apiFetch<ActorFilmographyResponse>(
    `/api/v1/movies/actors/filmography?${qs.toString()}`
  );
}

export function getPopularKeywords(limit = 50) {
  return apiFetch<PopularKeywordsResponse>(
    `/api/v1/movies/keywords/popular?limit=${limit}`
  );
}

export function searchKeywords(q: string, limit = 20) {
  return apiFetch<KeywordSearchResponse>(
    `/api/v1/movies/keywords/search?q=${encodeURIComponent(q)}&limit=${limit}`
  );
}

export function getKeywordMovies(
  keyword: string,
  params: { offset?: number; limit?: number } = {}
) {
  const qs = new URLSearchParams({ keyword });
  if (params.offset != null) qs.set("offset", String(params.offset));
  if (params.limit != null) qs.set("limit", String(params.limit));
  return apiFetch<KeywordMoviesResponse>(
    `/api/v1/movies/keywords/movies?${qs.toString()}`
  );
}
