import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getExplanation, getRecommendations } from "../../api/recommendations";
import type { RecommendationItem } from "../../api/types";
import ErrorPanel from "../../components/ErrorPanel";
import LoadingSpinner from "../../components/LoadingSpinner";
import MovieCard from "../../components/MovieCard";
import AddToListModal from "../../components/AddToListModal";
import { useDismissed } from "../../hooks/useDismissed";
import { useRated } from "../../hooks/useRated";
import { useUserId } from "../../hooks/useUserId";
import { useWatchlist } from "../../hooks/useWatchlist";

export default function RecommendationsTab() {
  const [params, setParams] = useSearchParams();
  const { userId } = useUserId();
  const [strategy, setStrategy] = useState(params.get("strategy") || "hybrid");
  const [topK, setTopK] = useState(Number(params.get("topK")) || 20);
  const [diversity, setDiversity] = useState<"low" | "medium" | "high">(
    (params.get("diversity") as "low" | "medium" | "high") || "medium"
  );
  const [recs, setRecs] = useState<RecommendationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fetched, setFetched] = useState(false);
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
    setParams({ user: String(userId), strategy, topK: String(topK), diversity });
    getRecommendations(userId, topK, strategy, diversity)
      .then((data) => {
        setRecs(data.recommendations);
        setFetched(true);
        const ids = data.recommendations.map((r) => r.movie.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        refreshRatingsForMovieIds(ids);
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  };

  // Auto-fetch if URL has params
  useEffect(() => {
    if (params.get("user") && !fetched) fetchRecs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleExplain = (movieId: number, movieTitle: string, score: number) => {
    setExplainMovieId(movieId);
    setExplainTitle(movieTitle);
    setExplainText("");
    setExplainError("");
    setExplainLoading(true);
    getExplanation(userId, movieId, score)
      .then((data) => setExplainText(data.explanation))
      .catch((e) => setExplainError(e.detail || e.message || "LLM unavailable"))
      .finally(() => setExplainLoading(false));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchRecs();
  };

  return (
    <>
      <header className="mb-12">
        <h1 className="text-5xl font-extrabold font-headline text-on-surface tracking-tight mb-2">
          Showing <span className="text-primary-container capitalize">{strategy}</span> recommendations
          {diversity !== "medium" && (
            <span className="text-lg font-bold text-on-surface-variant ml-3">
              ({diversity === "high" ? "adventurous" : "safe"} diversity)
            </span>
          )}
        </h1>
        {userId && (
          <p className="text-on-surface-variant text-lg">
            Curated intelligence for user{" "}
            <span className="text-on-surface font-mono bg-surface-container px-2 py-0.5 rounded">
              USR-{userId}
            </span>
          </p>
        )}
      </header>

      {/* Configuration Panel */}
      <section className="mb-16">
        <div className="glass-panel p-8 rounded-xl border border-outline-variant/10 shadow-2xl">
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 items-end">
            <div className="space-y-3">
              <label className="block text-xs font-bold uppercase tracking-widest text-on-surface-variant">Your ID</label>
              <div className="relative">
                <div className="w-full bg-surface-container-lowest text-on-surface h-12 px-4 rounded-lg font-mono flex items-center">
                  USR-{userId}
                </div>
                <span className="material-symbols-outlined absolute right-3 top-3 text-outline text-sm">fingerprint</span>
              </div>
            </div>
            <div className="space-y-3">
              <label className="block text-xs font-bold uppercase tracking-widest text-on-surface-variant">Strategy Engine</label>
              <select
                value={strategy}
                onChange={(e) => setStrategy(e.target.value)}
                className="w-full bg-surface-container-lowest border-0 focus:ring-2 focus:ring-primary-container/50 text-on-surface h-12 px-4 rounded-lg appearance-none cursor-pointer transition-all"
              >
                <option value="hybrid">Hybrid (Recommended)</option>
                <option value="content">Content-Based</option>
                <option value="collab">Collaborative Filtering</option>
              </select>
            </div>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <label className="block text-xs font-bold uppercase tracking-widest text-on-surface-variant">Top K Results</label>
                <span className="text-primary-container font-bold text-sm">{topK}</span>
              </div>
              <input
                type="range"
                min="1"
                max="100"
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="w-full h-1.5 bg-surface-container-highest rounded-lg appearance-none cursor-pointer accent-primary-container"
              />
            </div>
            <div className="space-y-3">
              <label className="block text-xs font-bold uppercase tracking-widest text-on-surface-variant">Diversity</label>
              <div className="flex gap-1">
                {([
                  { value: "low" as const, label: "Safe", icon: "target" },
                  { value: "medium" as const, label: "Balanced", icon: "balance" },
                  { value: "high" as const, label: "Adventurous", icon: "explore" },
                ]).map((opt) => (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => setDiversity(opt.value)}
                    className={`flex-1 h-12 rounded-lg text-xs font-bold tracking-wide transition-all flex flex-col items-center justify-center gap-0.5 ${
                      diversity === opt.value
                        ? "bg-primary-container text-on-primary-container shadow-[0_0_12px_rgba(255,193,7,0.25)]"
                        : "bg-surface-container-lowest text-on-surface-variant hover:bg-surface-container"
                    }`}
                  >
                    <span className="material-symbols-outlined text-sm">{opt.icon}</span>
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <button
                type="submit"
                className="w-full h-12 bg-primary-container text-on-primary-container font-bold rounded-lg flex items-center justify-center gap-2 hover:bg-primary transition-all active:scale-95 duration-150 shadow-[0_0_20px_rgba(255,193,7,0.2)]"
              >
                <span className="material-symbols-outlined">bolt</span>
                Get Recommendations
              </button>
            </div>
          </form>
        </div>
      </section>

      {loading && <LoadingSpinner text="Consulting the cinematic Oracle..." />}
      {error && <ErrorPanel message={error} onRetry={fetchRecs} />}

      {!loading && !error && (
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

      {!loading && !error && fetched && recs.length === 0 && (
        <p className="text-center text-on-surface-variant text-lg py-20">
          No recommendations found for this user.
        </p>
      )}

      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
    </>
  );
}
