import { useEffect, useState } from "react";
import { getTrendingMovies } from "../api/movies";
import type { TrendingMovieResult } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useWatchlist } from "../hooks/useWatchlist";

const WINDOW_OPTIONS = [
  { value: 7, label: "This week" },
  { value: 14, label: "2 weeks" },
  { value: 30, label: "This month" },
  { value: 90, label: "3 months" },
];

export default function Trending() {
  const [window, setWindow] = useState(7);
  const [results, setResults] = useState<TrendingMovieResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();

  const fetchTrending = (w: number) => {
    setLoading(true);
    setError("");
    getTrendingMovies(w, 40)
      .then((data) => {
        setResults(data.results);
        refreshForMovieIds(data.results.map((r) => r.movie.id));
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchTrending(window);
  }, [window]);

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <header className="mb-10">
            <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
              Trending Now
            </h1>
            <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
              Most rated movies by the community
            </p>
          </header>

          {/* Window selector */}
          <div className="flex gap-2 mb-10">
            {WINDOW_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setWindow(opt.value)}
                className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                  window === opt.value
                    ? "bg-primary-container text-on-primary-container shadow-md"
                    : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {loading && <LoadingSpinner text="Loading trending movies..." />}
          {error && <ErrorPanel message={error} onRetry={() => fetchTrending(window)} />}

          {!loading && !error && (
            <>
              <p className="text-on-surface-variant text-sm mb-6">
                <span className="font-bold text-on-surface">{results.length}</span> trending movie{results.length !== 1 ? "s" : ""}
              </p>
              <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
                {results.map((item, index) => (
                  <div key={item.movie.id} className="relative">
                    <div className="absolute -top-2 -left-2 z-10 bg-[#FFC107] text-[#131314] w-8 h-8 rounded-full flex items-center justify-center text-xs font-black shadow-lg">
                      {index + 1}
                    </div>
                    <MovieCard
                      movie={item.movie}
                      isBookmarked={isInWatchlist(item.movie.id)}
                      onToggleBookmark={toggle}
                    />
                    <p className="mt-2 text-xs text-on-surface-variant font-medium">
                      <span className="material-symbols-outlined text-sm align-middle mr-1">bar_chart</span>
                      {item.rating_count.toLocaleString()} rating{item.rating_count !== 1 ? "s" : ""}
                    </p>
                  </div>
                ))}
              </section>
            </>
          )}

          {!loading && !error && results.length === 0 && (
            <p className="text-center text-on-surface-variant text-lg py-20">
              No trending movies found for this time window. Try a longer period.
            </p>
          )}
        </div>
      </main>
      <BottomNav />
    </>
  );
}
