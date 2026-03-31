import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { searchMovies } from "../api/movies";
import type { MovieSummary } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useDismissed } from "../hooks/useDismissed";
import { useRated } from "../hooks/useRated";
import { useWatchlist } from "../hooks/useWatchlist";

export default function Search() {
  const [params] = useSearchParams();
  const q = params.get("q") || "";
  const [results, setResults] = useState<MovieSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();

  useEffect(() => {
    if (!q) return;
    setLoading(true);
    setError("");
    searchMovies(q, 40)
      .then((data) => {
        setResults(data.results);
        setTotal(data.total);
        { const _ids = data.results.map((m) => m.id); refreshForMovieIds(_ids); refreshDismissedForMovieIds(_ids); refreshRatingsForMovieIds(_ids); }
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  }, [q]);

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <header className="mb-12">
            <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
              {q ? (
                <>
                  Found <span className="text-primary-container">{total}</span> results
                  for <span className="italic text-primary">"{q}"</span>
                </>
              ) : (
                "Search for movies"
              )}
            </h1>
            <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
              CineMatch-AI Intelligence Engine
            </p>
          </header>

          {loading && <LoadingSpinner text="Syncing cinematic metadata..." />}
          {error && <ErrorPanel message={error} onRetry={() => window.location.reload()} />}

          {!loading && !error && (
            <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
              {results.map((movie) => (
                <MovieCard key={movie.id} movie={movie} isBookmarked={isInWatchlist(movie.id)} onToggleBookmark={toggle} isDismissed={isDismissed(movie.id)} onDismiss={toggleDismiss} userRating={getRating(movie.id)} />
              ))}
            </section>
          )}

          {!loading && !error && results.length === 0 && q && (
            <p className="text-center text-on-surface-variant text-lg py-20">
              No movies found. Try a different search.
            </p>
          )}
        </div>
      </main>
      <BottomNav />
    </>
  );
}
