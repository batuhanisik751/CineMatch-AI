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

export interface RecommendationExplanation {
  movie_id: number;
  title: string;
  explanation: string;
  score: number;
}
