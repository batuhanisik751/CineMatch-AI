import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { getRecommendations } from "../api/recommendations";
import type { RecommendationItem } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";

export default function Recommendations() {
  const [params, setParams] = useSearchParams();
  const { userId } = useUserId();
  const [strategy, setStrategy] = useState(params.get("strategy") || "hybrid");
  const [topK, setTopK] = useState(20);
  const [recs, setRecs] = useState<RecommendationItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [fetched, setFetched] = useState(false);

  const fetchRecs = () => {
    setLoading(true);
    setError("");
    setParams({ user: String(userId), strategy });
    getRecommendations(userId, topK, strategy)
      .then((data) => {
        setRecs(data.recommendations);
        setFetched(true);
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  };

  // Auto-fetch if URL has params
  useEffect(() => {
    if (params.get("user") && !fetched) fetchRecs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchRecs();
  };

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="lg:ml-64 pt-32 px-8 pb-20 max-w-7xl mx-auto">
        <header className="mb-12">
          <h1 className="text-5xl font-extrabold font-headline text-on-surface tracking-tight mb-2">
            Showing <span className="text-primary-container capitalize">{strategy}</span> recommendations
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
            <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 items-end">
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
              <MovieCard
                key={rec.movie.id}
                movie={rec.movie}
                matchPercent={Math.round(rec.score * 100)}
              />
            ))}
          </div>
        )}

        {!loading && !error && fetched && recs.length === 0 && (
          <p className="text-center text-on-surface-variant text-lg py-20">
            No recommendations found for this user.
          </p>
        )}
      </main>
      <BottomNav />
    </>
  );
}
