import { apiFetch } from "./client";
import type {
  AutocompleteResponse,
  ActorFilmographyResponse,
  ActorSearchResponse,
  AdvancedSearchResponse,
  ControversialResponse,
  MovieRatingStatsResponse,
  DecadeMoviesResponse,
  DecadesResponse,
  DirectorFilmographyResponse,
  DirectorSearchResponse,
  GenresResponse,
  LanguagesResponse,
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
  ThematicCollectionDetailResponse,
  ThematicCollectionsResponse,
  TopChartsResponse,
  TrendingResponse,
  MovieConnectionsResponse,
  MovieActivityResponse,
  MovieDNAResponse,
  MoviePathResponse,
} from "./types";

export function autocompleteMovies(q: string, limit = 8, signal?: AbortSignal) {
  return apiFetch<AutocompleteResponse>(
    `/api/v1/movies/autocomplete?q=${encodeURIComponent(q)}&limit=${limit}`,
    { signal },
  );
}

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
  language?: string;
  min_runtime?: number;
  max_runtime?: number;
  sort_by?: string;
  offset?: number;
  limit?: number;
}) {
  const qs = new URLSearchParams();
  if (params.genre) qs.set("genre", params.genre);
  if (params.year_min != null) qs.set("year_min", String(params.year_min));
  if (params.year_max != null) qs.set("year_max", String(params.year_max));
  if (params.language) qs.set("language", params.language);
  if (params.min_runtime != null) qs.set("min_runtime", String(params.min_runtime));
  if (params.max_runtime != null) qs.set("max_runtime", String(params.max_runtime));
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

export function getLanguages() {
  return apiFetch<LanguagesResponse>("/api/v1/movies/languages");
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

export function advancedSearchMovies(params: {
  genre?: string;
  decade?: string;
  min_rating?: number;
  max_rating?: number;
  director?: string;
  keyword?: string;
  cast?: string;
  language?: string;
  min_runtime?: number;
  max_runtime?: number;
  sort_by?: string;
  offset?: number;
  limit?: number;
}) {
  const qs = new URLSearchParams();
  if (params.genre) qs.set("genre", params.genre);
  if (params.decade) qs.set("decade", params.decade);
  if (params.min_rating != null) qs.set("min_rating", String(params.min_rating));
  if (params.max_rating != null) qs.set("max_rating", String(params.max_rating));
  if (params.director) qs.set("director", params.director);
  if (params.keyword) qs.set("keyword", params.keyword);
  if (params.cast) qs.set("cast", params.cast);
  if (params.language) qs.set("language", params.language);
  if (params.min_runtime != null) qs.set("min_runtime", String(params.min_runtime));
  if (params.max_runtime != null) qs.set("max_runtime", String(params.max_runtime));
  if (params.sort_by) qs.set("sort_by", params.sort_by);
  if (params.offset != null) qs.set("offset", String(params.offset));
  if (params.limit != null) qs.set("limit", String(params.limit));
  return apiFetch<AdvancedSearchResponse>(`/api/v1/movies/advanced-search?${qs.toString()}`);
}

export function getControversialMovies(
  params: { min_ratings?: number; limit?: number } = {},
) {
  const qs = new URLSearchParams();
  if (params.min_ratings != null)
    qs.set("min_ratings", String(params.min_ratings));
  if (params.limit != null) qs.set("limit", String(params.limit));
  return apiFetch<ControversialResponse>(
    `/api/v1/movies/controversial?${qs.toString()}`,
  );
}

export function getMovieRatingStats(movieId: number, userId?: number) {
  const qs = new URLSearchParams();
  if (userId != null) qs.set("user_id", String(userId));
  const query = qs.toString();
  return apiFetch<MovieRatingStatsResponse>(
    `/api/v1/movies/${movieId}/rating-stats${query ? `?${query}` : ""}`,
  );
}

export function getThematicCollections(type?: string) {
  const qs = new URLSearchParams();
  if (type) qs.set("collection_type", type);
  const query = qs.toString();
  return apiFetch<ThematicCollectionsResponse>(
    `/api/v1/movies/thematic-collections${query ? `?${query}` : ""}`,
  );
}

export function getThematicCollectionDetail(id: string, limit = 20) {
  return apiFetch<ThematicCollectionDetailResponse>(
    `/api/v1/movies/thematic-collections/${encodeURIComponent(id)}?limit=${limit}`,
  );
}

export function getMovieConnections(id1: number, id2: number) {
  return apiFetch<MovieConnectionsResponse>(
    `/api/v1/movies/${id1}/connection/${id2}`,
  );
}

export function getMoviePath(id1: number, id2: number, maxDepth = 6) {
  return apiFetch<MoviePathResponse>(
    `/api/v1/movies/${id1}/path/${id2}?max_depth=${maxDepth}`,
  );
}

export function getMovieDNA(movieId: number) {
  return apiFetch<MovieDNAResponse>(
    `/api/v1/movies/${movieId}/dna`,
  );
}

export function getMovieActivity(movieId: number, granularity = "month") {
  return apiFetch<MovieActivityResponse>(
    `/api/v1/movies/${movieId}/activity?granularity=${granularity}`,
  );
}
