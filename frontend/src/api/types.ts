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
  diversity: "low" | "medium" | "high";
  recommendations: RecommendationItem[];
}

export interface FromSeedRecommendationsResponse extends RecommendationsResponse {
  seed_movie: MovieSummary;
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

export interface DismissalResponse {
  user_id: number;
  movie_id: number;
  dismissed_at: string;
  movie_title: string | null;
}

export interface DismissalItemResponse {
  user_id: number;
  movie_id: number;
  dismissed_at: string;
  movie_title: string | null;
  poster_path: string | null;
  genres: string[];
  vote_average: number;
  release_date: string | null;
}

export interface DismissalListResponse {
  user_id: number;
  items: DismissalItemResponse[];
  total: number;
  offset: number;
  limit: number;
}

export interface DismissalBulkStatusResponse {
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

export interface FeedSection {
  key: string;
  title: string;
  movies: MovieSummary[];
}

export interface FeedResponse {
  user_id: number;
  is_personalized: boolean;
  sections: FeedSection[];
}

export interface DiaryDayMovie {
  id: number;
  title: string | null;
  rating: number;
}

export interface DiaryDay {
  date: string;
  count: number;
  movies: DiaryDayMovie[];
}

export interface DiaryResponse {
  user_id: number;
  year: number;
  days: DiaryDay[];
  total_ratings: number;
}

export interface RatingComparisonMovie {
  movie_id: number;
  title: string;
  poster_path: string | null;
  user_rating: number;
  community_avg: number;
  difference: number;
}

export interface RatingComparisonResponse {
  user_id: number;
  user_avg: number;
  community_avg: number;
  agreement_pct: number;
  total_rated: number;
  most_overrated: RatingComparisonMovie[];
  most_underrated: RatingComparisonMovie[];
}

export interface RatedFilm {
  movie_id: number;
  title: string;
  rating: number;
  poster_path: string | null;
}

export interface AffinityEntry {
  name: string;
  role: string;
  avg_rating: number;
  count: number;
  weighted_score: number;
  films_rated: RatedFilm[];
}

export interface AffinitiesResponse {
  user_id: number;
  directors: AffinityEntry[];
  actors: AffinityEntry[];
}

export interface TasteInsight {
  key: string;
  icon: string;
  text: string;
}

export interface TasteProfileResponse {
  user_id: number;
  total_ratings: number;
  insights: TasteInsight[];
  llm_summary: string | null;
}

export interface RatingHistogramBucket {
  rating: number;
  count: number;
}

export interface ControversialMovieResult {
  movie: MovieSummary;
  avg_rating: number;
  stddev_rating: number;
  rating_count: number;
  histogram: RatingHistogramBucket[];
}

export interface ControversialResponse {
  results: ControversialMovieResult[];
  min_ratings: number;
  limit: number;
}

export interface MovieRatingStatsResponse {
  movie_id: number;
  avg_rating: number;
  median_rating: number;
  total_ratings: number;
  stddev: number;
  polarization_score: number;
  distribution: RatingHistogramBucket[];
  user_rating: number | null;
}

export interface Milestone {
  threshold: number;
  reached: boolean;
  label: string;
}

export interface StreakResponse {
  user_id: number;
  current_streak: number;
  longest_streak: number;
  total_ratings: number;
  milestones: Milestone[];
}

export interface TasteEvolutionPeriod {
  period: string;
  genres: Record<string, number>;
}

export interface TasteEvolutionResponse {
  user_id: number;
  granularity: string;
  periods: TasteEvolutionPeriod[];
}

// Custom user lists

export interface UserListSummary {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  is_public: boolean;
  movie_count: number;
  preview_posters: string[];
  created_at: string;
  updated_at: string;
}

export interface UserListItemResponse {
  movie_id: number;
  position: number;
  added_at: string;
  movie_title: string | null;
  poster_path: string | null;
  genres: string[];
  vote_average: number;
  release_date: string | null;
}

export interface UserListDetailResponse {
  id: number;
  user_id: number;
  name: string;
  description: string | null;
  is_public: boolean;
  movie_count: number;
  items: UserListItemResponse[];
  total: number;
  offset: number;
  limit: number;
  created_at: string;
  updated_at: string;
}

export interface UserListsResponse {
  user_id: number;
  lists: UserListSummary[];
  total: number;
}

export interface PopularListsResponse {
  lists: UserListSummary[];
  total: number;
  offset: number;
  limit: number;
}

// Global platform stats

export interface GlobalStatsMovieRef {
  id: number;
  title: string;
  poster_path: string | null;
  vote_average: number;
  genres: string[];
  release_date: string | null;
  rating_count: number;
  avg_user_rating: number | null;
}

export interface GlobalStatsUserRef {
  id: number;
  movielens_id: number;
  rating_count: number;
}

export interface GlobalStatsResponse {
  total_movies: number;
  total_users: number;
  total_ratings: number;
  avg_rating: number;
  most_rated_movie: GlobalStatsMovieRef | null;
  highest_rated_movie: GlobalStatsMovieRef | null;
  most_active_user: GlobalStatsUserRef | null;
  ratings_this_week: number;
}

export interface ThematicCollectionSummary {
  id: string;
  title: string;
  collection_type: string;
  movie_count: number;
  preview_posters: string[];
}

export interface ThematicCollectionsResponse {
  results: ThematicCollectionSummary[];
  collection_type: string | null;
}

export interface ThematicCollectionMovieResult {
  movie: MovieSummary;
  avg_rating: number;
  rating_count: number;
}

export interface ThematicCollectionDetailResponse {
  id: string;
  title: string;
  collection_type: string;
  results: ThematicCollectionMovieResult[];
  total: number;
  limit: number;
}

export interface AchievementBadge {
  id: string;
  name: string;
  description: string;
  icon: string;
  unlocked: boolean;
  progress: number;
  target: number;
  unlocked_detail: string | null;
}

export interface AchievementResponse {
  user_id: number;
  badges: AchievementBadge[];
  unlocked_count: number;
  total_count: number;
}

export interface Challenge {
  id: string;
  template: string;
  title: string;
  description: string;
  icon: string;
  target: number;
  parameter: string;
}

export interface ChallengeWithProgress extends Challenge {
  progress: number;
  completed: boolean;
  qualifying_movie_ids: number[];
}

export interface BingoCell {
  index: number;
  template: string;
  label: string;
  parameter: string | null;
  completed: boolean;
  movie_id: number | null;
}

export interface BingoCardResponse {
  user_id: number;
  seed: string;
  cells: BingoCell[];
  completed_lines: number[][];
  total_completed: number;
  bingo_count: number;
}

export interface ChallengesCurrentResponse {
  week: string;
  challenges: Challenge[];
}

export interface ChallengesProgressResponse {
  user_id: number;
  week: string;
  challenges: ChallengeWithProgress[];
  completed_count: number;
  total_count: number;
}

export interface MovieConnectionItem {
  type: string;
  value: string;
  details: string;
}

export interface MovieConnectionsResponse {
  movie1: MovieSummary;
  movie2: MovieSummary;
  connections: MovieConnectionItem[];
  connection_count: number;
}

export interface PathStep {
  movie: MovieSummary;
  linked_by: string | null;
}

export interface MoviePathResponse {
  movie1: MovieSummary;
  movie2: MovieSummary;
  path: PathStep[];
  degrees: number;
  found: boolean;
}

export interface GenreWeight {
  genre: string;
  weight: number;
}

export interface KeywordWeight {
  keyword: string;
  weight: number;
}

export interface MovieDNAResponse {
  movie_id: number;
  title: string;
  genres: GenreWeight[];
  top_keywords: KeywordWeight[];
  decade: number | null;
  mood_tags: string[];
  director: string | null;
  vote_average: number;
}

export interface ActivityPeriod {
  period: string;
  rating_count: number;
  avg_rating: number;
}

export interface MovieActivityResponse {
  movie_id: number;
  granularity: string;
  timeline: ActivityPeriod[];
  total_ratings: number;
}

export interface AutocompleteSuggestion {
  id: number;
  title: string;
  year: number | null;
  poster_path: string | null;
}

export interface AutocompleteResponse {
  results: AutocompleteSuggestion[];
  query: string;
}
