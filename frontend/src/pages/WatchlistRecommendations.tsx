import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getExplanation } from "../api/recommendations";
import { getWatchlistRecommendations } from "../api/watchlist";
import type { RecommendationsResponse, RecommendationItem } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import AddToListModal from "../components/AddToListModal";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useDismissed } from "../hooks/useDismissed";
import { useRated } from "../hooks/useRated";
import { useUserId } from "../hooks/useUserId";
import { useWatchlist } from "../hooks/useWatchlist";

export default function WatchlistRecommendations() {
  const { userId } = useUserId();
  const [data, setData] = useState<RecommendationsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [explainMovieId, setExplainMovieId] = useState<number | null>(null);
  const [explainTitle, setExplainTitle] = useState("");
  const [explainText, setExplainText] = useState("");
  const [explainLoading, setExplainLoading] = useState(false);
  const [explainError, setExplainError] = useState("");
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  const fetchRecs = () => {
    setLoading(true);
    setError("");
    getWatchlistRecommendations(userId)
      .then((res) => {
        setData(res);
        const ids = res.recommendations.map((r) => r.movie.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        refreshRatingsForMovieIds(ids);
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchRecs();
  }, [userId]);

  const handleExplain = (id: number, title: string, score: number) => {
    setExplainMovieId(id);
    setExplainTitle(title);
    setExplainText("");
    setExplainError("");
    setExplainLoading(true);
    getExplanation(userId, id, score)
      .then((d) => setExplainText(d.explanation))
      .catch((e) => setExplainError(e.detail || e.message || "LLM unavailable"))
      .finally(() => setExplainLoading(false));
  };

  const recs: RecommendationItem[] = data?.recommendations ?? [];

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="lg:ml-64 pt-32 px-8 pb-20 max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-12">
          <Link
            to="/watchlist"
            className="inline-flex items-center gap-2 text-on-surface-variant hover:text-primary text-sm mb-6 transition-colors"
          >
            <span className="material-symbols-outlined text-lg">arrow_back</span>
            Back to watchlist
          </Link>

          <h1 className="text-4xl md:text-5xl font-extrabold font-headline text-on-surface tracking-tight mb-2">
            WATCHLIST{" "}
            <span className="text-primary-container">PICKS</span>
          </h1>
          <p className="text-on-surface-variant text-lg">
            Movies similar to what you've saved
          </p>
        </header>

        {loading && <LoadingSpinner text="Analyzing your watchlist..." />}
        {error && <ErrorPanel message={error} onRetry={fetchRecs} />}

        {!loading && !error && recs.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-10">
            {recs.map((rec) => (
              <div key={rec.movie.id} className="flex flex-col">
                <MovieCard
                  movie={rec.movie}
                  matchPercent={Math.round(rec.score * 100)}
                  isBookmarked={isInWatchlist(rec.movie.id)}
                  onToggleBookmark={toggle}
                  onAddToList={(id) => setAddToListMovieId(id)}
                  isDismissed={isDismissed(rec.movie.id)}
                  onDismiss={toggleDismiss}
                  featureExplanations={rec.feature_explanations}
                  scoreBreakdown={rec.score_breakdown}
                  userRating={getRating(rec.movie.id)}
                />
                <button
                  onClick={() => handleExplain(rec.movie.id, rec.movie.title, rec.score)}
                  className="mt-2 w-full text-xs font-bold uppercase tracking-widest text-on-surface-variant hover:text-primary-container flex items-center justify-center gap-1 py-1 transition-colors"
                >
                  <span className="material-symbols-outlined text-sm">psychology</span>
                  Why This?
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Explanation modal */}
        {explainMovieId !== null && (
          <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            onClick={() => setExplainMovieId(null)}
          >
            <div
              className="glass-panel rounded-xl border border-outline-variant/20 shadow-2xl p-8 max-w-lg w-full mx-4"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-1">Why This?</p>
                  <h3 className="text-xl font-bold text-on-surface">{explainTitle}</h3>
                </div>
                <button
                  onClick={() => setExplainMovieId(null)}
                  className="text-outline hover:text-on-surface transition-colors ml-4"
                >
                  <span className="material-symbols-outlined">close</span>
                </button>
              </div>
              {explainLoading && (
                <div className="flex items-center gap-3 text-on-surface-variant py-4">
                  <span className="material-symbols-outlined animate-spin">progress_activity</span>
                  Mistral is thinking...
                </div>
              )}
              {explainError && (
                <p className="text-error text-sm py-4">{explainError}</p>
              )}
              {explainText && (
                <p className="text-on-surface leading-relaxed">{explainText}</p>
              )}
            </div>
          </div>
        )}

        {!loading && !error && recs.length === 0 && (
          <div className="text-center py-24">
            <span className="material-symbols-outlined text-6xl text-outline mb-4 block">
              bookmark
            </span>
            <p className="text-on-surface-variant text-lg mb-6">
              Add movies to your watchlist to get personalized picks
            </p>
            <Link
              to="/discover/browse"
              className="inline-block bg-primary-container/20 border border-primary-container/40 text-primary px-6 py-3 rounded-md font-bold hover:bg-primary-container hover:text-on-primary-container transition-all"
            >
              Discover Movies
            </Link>
          </div>
        )}
      </main>
      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
      <BottomNav />
    </>
  );
}
