import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { searchMovies } from "../../api/movies";
import type { MovieSummary } from "../../api/types";
import ErrorPanel from "../../components/ErrorPanel";
import LoadingSpinner from "../../components/LoadingSpinner";
import MovieCard from "../../components/MovieCard";
import AddToListModal from "../../components/AddToListModal";
import { useDismissed } from "../../hooks/useDismissed";
import { useRated } from "../../hooks/useRated";
import { useMatchPredictions } from "../../hooks/useMatchPredictions";
import { useWatchlist } from "../../hooks/useWatchlist";

export default function TitleTab() {
  const [params, setParams] = useSearchParams();
  const q = params.get("q") || "";
  const [input, setInput] = useState(q);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  // Sync input when URL param changes externally (e.g. browser back)
  useEffect(() => { setInput(q); }, [q]);

  const handleInputChange = (value: string) => {
    setInput(value);
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      if (value.trim()) {
        setParams({ q: value.trim() });
      } else {
        setParams({});
      }
    }, 500);
  };
  const [results, setResults] = useState<MovieSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const { getMatchPercent, fetchMatchPercents } = useMatchPredictions();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  useEffect(() => {
    if (!q) return;
    setLoading(true);
    setError("");
    searchMovies(q, 40)
      .then((data) => {
        setResults(data.results);
        setTotal(data.total);
        { const _ids = data.results.map((m) => m.id); refreshForMovieIds(_ids); refreshDismissedForMovieIds(_ids); refreshRatingsForMovieIds(_ids); fetchMatchPercents(_ids); }
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  }, [q]);

  return (
    <>
      <header className="mb-8">
        <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
          Search for movies
        </h1>
        <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
          CineMatch-AI Intelligence Engine
        </p>
      </header>

      <div className="mb-10">
        <div className="relative max-w-2xl">
          <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline/60 text-xl">search</span>
          <input
            type="text"
            value={input}
            onChange={(e) => handleInputChange(e.target.value)}
            placeholder="Type a movie title..."
            className="w-full h-12 pl-12 pr-5 bg-surface-container-lowest border border-outline-variant/20 rounded-full text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint focus:outline-none font-body text-base"
          />
          {input && (
            <button
              onClick={() => handleInputChange("")}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
            >
              <span className="material-symbols-outlined text-xl">close</span>
            </button>
          )}
        </div>
      </div>

      {q && (
        <p className="mb-6 text-on-surface-variant text-sm">
          Found <span className="text-primary-container font-bold">{total}</span> results
          for <span className="italic text-primary">"{q}"</span>
        </p>
      )}

      {loading && <LoadingSpinner text="Syncing cinematic metadata..." />}
      {error && <ErrorPanel message={error} onRetry={() => window.location.reload()} />}

      {!loading && !error && (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {results.map((movie) => (
            <MovieCard key={movie.id} movie={movie} isBookmarked={isInWatchlist(movie.id)} onToggleBookmark={toggle} onAddToList={(id) => setAddToListMovieId(id)} isDismissed={isDismissed(movie.id)} onDismiss={toggleDismiss} userRating={getRating(movie.id)} matchPercent={getMatchPercent(movie.id)} />
          ))}
        </section>
      )}

      {!loading && !error && results.length === 0 && q && (
        <p className="text-center text-on-surface-variant text-lg py-20">
          No movies found. Try a different search.
        </p>
      )}

      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
    </>
  );
}
