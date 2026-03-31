import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getExplanation, getFromSeedRecommendations } from "../api/recommendations";
import type { FromSeedRecommendationsResponse, RecommendationItem } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useDismissed } from "../hooks/useDismissed";
import { useRated } from "../hooks/useRated";
import { useUserId } from "../hooks/useUserId";
import { useWatchlist } from "../hooks/useWatchlist";

function posterUrl(path: string | null, size = "w200") {
  return path ? `https://image.tmdb.org/t/p/${size}${path}` : null;
}

export default function FromSeedRecommendations() {
  const { movieId } = useParams<{ movieId: string }>();
  const { userId } = useUserId();
  const [data, setData] = useState<FromSeedRecommendationsResponse | null>(null);
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

  useEffect(() => {
    if (!movieId) return;
    setLoading(true);
    setError("");
    getFromSeedRecommendations(userId, Number(movieId))
      .then((res) => {
        setData(res);
        const ids = res.recommendations.map((r) => r.movie.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        refreshRatingsForMovieIds(ids);
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  }, [movieId, userId]);

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
  const seed = data?.seed_movie ?? null;

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="lg:ml-64 pt-32 px-8 pb-20 max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-12">
          <Link
            to={seed ? `/movies/${seed.id}` : "#"}
            className="inline-flex items-center gap-2 text-on-surface-variant hover:text-primary text-sm mb-6 transition-colors"
          >
            <span className="material-symbols-outlined text-lg">arrow_back</span>
            Back to movie
          </Link>

          <div className="flex items-center gap-6">
            {seed && (
              <div className="w-20 shrink-0 hidden sm:block">
                {posterUrl(seed.poster_path) ? (
                  <img
                    src={posterUrl(seed.poster_path)!}
                    alt={seed.title}
                    className="w-full aspect-[2/3] object-cover rounded-lg shadow-lg"
                  />
                ) : (
                  <div className="w-full aspect-[2/3] bg-surface-container rounded-lg flex items-center justify-center">
                    <span className="material-symbols-outlined text-2xl text-outline">movie</span>
                  </div>
                )}
              </div>
            )}
            <div>
              <h1 className="text-4xl md:text-5xl font-extrabold font-headline text-on-surface tracking-tight mb-2">
                More Like{" "}
                <span className="text-primary-container">{seed?.title ?? "..."}</span>
              </h1>
              <p className="text-on-surface-variant text-lg">
                Personalized picks branching from this movie
              </p>
            </div>
          </div>
        </header>

        {loading && <LoadingSpinner text="Finding similar movies for you..." />}
        {error && (
          <ErrorPanel
            message={error}
            onRetry={() => {
              if (movieId) {
                setLoading(true);
                setError("");
                getFromSeedRecommendations(userId, Number(movieId))
                  .then((res) => {
                    setData(res);
                    const ids = res.recommendations.map((r) => r.movie.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        refreshRatingsForMovieIds(ids);
                  })
                  .catch((e) => setError(e.detail || e.message))
                  .finally(() => setLoading(false));
              }
            }}
          />
        )}

        {!loading && !error && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-10">
            {recs.map((rec) => (
              <div key={rec.movie.id} className="flex flex-col">
                <MovieCard
                  movie={rec.movie}
                  matchPercent={Math.round(rec.score * 100)}
                  isBookmarked={isInWatchlist(rec.movie.id)}
                  onToggleBookmark={toggle}
                  isDismissed={isDismissed(rec.movie.id)}
                  onDismiss={toggleDismiss}
                  becauseYouLiked={rec.because_you_liked?.title ?? null}
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
          <p className="text-center text-on-surface-variant text-lg py-20">
            No similar recommendations found for this movie.
          </p>
        )}
      </main>
      <BottomNav />
    </>
  );
}
