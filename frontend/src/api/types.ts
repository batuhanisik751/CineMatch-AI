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

export interface TrendingMovieResult {
  movie: MovieSummary;
  rating_count: number;
}

export interface TrendingResponse {
  results: TrendingMovieResult[];
  window: number;
  limit: number;
}

export interface HiddenGemResult {
  movie: MovieSummary;
  vote_average: number;
  vote_count: number;
}

export interface HiddenGemsResponse {
  results: HiddenGemResult[];
  min_rating: number;
  max_votes: number;
  limit: number;
}

export interface TopChartResult {
  movie: MovieSummary;
  avg_rating: number;
  rating_count: number;
}

export interface TopChartsResponse {
  results: TopChartResult[];
  genre: string;
  limit: number;
}

export interface DecadeSummary {
  decade: number;
  movie_count: number;
  avg_rating: number;
}

export interface DecadesResponse {
  decades: DecadeSummary[];
}

export interface DecadeMovieResult {
  movie: MovieSummary;
  avg_rating: number;
  rating_count: number;
}

export interface DecadeMoviesResponse {
  results: DecadeMovieResult[];
  decade: number;
  genre: string | null;
  total: number;
  offset: number;
  limit: number;
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

export interface SeedInfluence {
  movie_id: number;
  title: string;
  your_rating: number;
}

export interface ScoreBreakdown {
  content_score: number;
  collab_score: number;
  alpha: number;
}

export interface RecommendationItem {
  movie: MovieSummary;
  score: number;
  content_score: number | null;
  collab_score: number | null;
  because_you_liked: SeedInfluence | null;
  feature_explanations: string[];
  score_breakdown: ScoreBreakdown | null;
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

export interface MoodRecommendationItem {
  movie: MovieSummary;
  similarity: number;
}

export interface MoodRecommendationResponse {
  user_id: number;
  mood: string;
  alpha: number;
  is_personalized: boolean;
  results: MoodRecommendationItem[];
  total: number;
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

export interface DirectorSummary {
  name: string;
  film_count: number;
  avg_vote: number;
}

export interface DirectorSearchResponse {
  results: DirectorSummary[];
  query: string;
}

export interface PopularDirectorsResponse {
  results: DirectorSummary[];
  limit: number;
}

export interface DirectorFilmResult {
  movie: MovieSummary;
  user_rating: number | null;
}

export interface DirectorStats {
  total_films: number;
  avg_vote: number;
  genres: string[];
  user_avg_rating: number | null;
  user_rated_count: number;
}

export interface DirectorFilmographyResponse {
  director: string;
  stats: DirectorStats;
  filmography: DirectorFilmResult[];
}

export interface ActorSummary {
  name: string;
  film_count: number;
  avg_vote: number;
}

export interface ActorSearchResponse {
  results: ActorSummary[];
  query: string;
}

export interface PopularActorsResponse {
  results: ActorSummary[];
  limit: number;
}

export interface ActorFilmResult {
  movie: MovieSummary;
  user_rating: number | null;
}

export interface ActorStats {
  total_films: number;
  avg_vote: number;
  genres: string[];
  user_avg_rating: number | null;
  user_rated_count: number;
}

export interface ActorFilmographyResponse {
  actor: string;
  stats: ActorStats;
  filmography: ActorFilmResult[];
}

export interface KeywordSummary {
  keyword: string;
  count: number;
}

export interface PopularKeywordsResponse {
  results: KeywordSummary[];
  limit: number;
}

export interface KeywordSearchResponse {
  results: KeywordSummary[];
  query: string;
}

export interface KeywordStats {
  total_movies: number;
  avg_vote: number;
  top_genres: string[];
}

export interface KeywordMovieResult {
  movie: MovieSummary;
  vote_average: number;
}

export interface KeywordMoviesResponse {
  results: KeywordMovieResult[];
  keyword: string;
  stats: KeywordStats;
  total: number;
  offset: number;
  limit: number;
}

export interface SurpriseResponse {
  user_id: number;
  excluded_genres: string[];
  results: MovieSummary[];
  limit: number;
}

export interface AdvancedSearchResult {
  movie: MovieSummary;
  vote_average: number;
  director: string | null;
}

export interface AdvancedSearchResponse {
  results: AdvancedSearchResult[];
  total: number;
  offset: number;
  limit: number;
}

export interface CollectionGroup {
  creator_type: string;
  creator_name: string;
  rated_count: number;
  avg_rating: number;
  total_by_creator: number;
  missing: MovieSummary[];
}

export interface CompletionsResponse {
  user_id: number;
  groups: CollectionGroup[];
  total_missing: number;
}
