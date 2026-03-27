export interface MovieSummary {
  id: number;
  title: string;
  genres: string[];
  vote_average: number;
  release_date: string | null;
  poster_path: string | null;
}

export interface MovieResponse {
  id: number;
  tmdb_id: number;
  imdb_id: string | null;
  title: string;
  overview: string | null;
  genres: string[];
  keywords: string[];
  cast_names: string[];
  director: string | null;
  release_date: string | null;
  vote_average: number;
  vote_count: number;
  popularity: number;
  poster_path: string | null;
}

export interface SimilarMovie {
  movie: MovieSummary;
  similarity: number;
}

export interface SimilarMoviesResponse {
  movie_id: number;
  movie_title: string;
  similar: SimilarMovie[];
}

export interface MovieSearchResponse {
  results: MovieSummary[];
  total: number;
  query: string;
}

export interface MovieListResponse {
  results: MovieSummary[];
  total: number;
  offset: number;
  limit: number;
}

export interface GenreCount {
  genre: string;
  count: number;
}

export interface GenresResponse {
  genres: GenreCount[];
}

export interface SemanticSearchResult {
  movie: MovieSummary;
  similarity: number;
}

export interface SemanticSearchResponse {
  results: SemanticSearchResult[];
  total: number;
  query: string;
}

export interface RatingResponse {
  user_id: number;
  movie_id: number;
  rating: number;
  timestamp: string;
  movie_title: string | null;
}

export interface UserRatingsResponse {
  user_id: number;
  ratings: RatingResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface RecommendationItem {
  movie: MovieSummary;
  score: number;
  content_score: number | null;
  collab_score: number | null;
}

export interface RecommendationsResponse {
  user_id: number;
  strategy: string;
  recommendations: RecommendationItem[];
}

export interface UserResponse {
  id: number;
  movielens_id: number;
  created_at: string;
}

export interface ApiError {
  detail: string;
}

export interface WatchlistItemResponse {
  user_id: number;
  movie_id: number;
  added_at: string;
  movie_title: string | null;
  poster_path: string | null;
  genres: string[];
  vote_average: number;
  release_date: string | null;
}

export interface WatchlistResponse {
  user_id: number;
  items: WatchlistItemResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface WatchlistBulkStatusResponse {
  movie_ids: number[];
}

export interface RecommendationExplanation {
  movie_id: number;
  title: string;
  explanation: string;
  score: number;
}

export interface StatsGenreCount {
  genre: string;
  count: number;
  percentage: number;
}

export interface RatingBucket {
  rating: string;
  count: number;
}

export interface PersonCount {
  name: string;
  count: number;
}

export interface MonthlyActivity {
  month: string;
  count: number;
}

export interface UserStatsResponse {
  user_id: number;
  total_ratings: number;
  average_rating: number;
  genre_distribution: StatsGenreCount[];
  rating_distribution: RatingBucket[];
  top_directors: PersonCount[];
  top_actors: PersonCount[];
  rating_timeline: MonthlyActivity[];
}
