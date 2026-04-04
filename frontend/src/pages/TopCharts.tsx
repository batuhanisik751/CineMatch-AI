import { useEffect, useState } from "react";
import { getGenres, getTopCharts } from "../api/movies";
import type { TopChartResult } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import AddToListModal from "../components/AddToListModal";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useDismissed } from "../hooks/useDismissed";
import { useRated } from "../hooks/useRated";
import { useWatchlist } from "../hooks/useWatchlist";

export default function TopCharts() {
  const [genre, setGenre] = useState<string | null>(null);
  const [genres, setGenres] = useState<string[]>([]);
  const [results, setResults] = useState<TopChartResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [genresLoaded, setGenresLoaded] = useState(false);
  const [error, setError] = useState("");
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  useEffect(() => {
    getGenres()
      .then((data) => {
        const names = data.genres.map((g) => g.genre);
        setGenres(names);
        if (names.length > 0 && genre === null) {
          setGenre(names[0]);
        }
      })
      .catch((e) => {
        setError(e.detail || e.message || "Failed to load genres");
        setLoading(false);
      })
      .finally(() => setGenresLoaded(true));
  }, []);

  const fetchTopCharts = (g: string) => {
    setLoading(true);
    setError("");
    getTopCharts(g, 40)
      .then((data) => {
        setResults(data.results);
        { const _ids = data.results.map((r) => r.movie.id); refreshForMovieIds(_ids); refreshDismissedForMovieIds(_ids); refreshRatingsForMovieIds(_ids); }
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (genre) {
      fetchTopCharts(genre);
    }
  }, [genre]);

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <header className="mb-10">
            <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
              Top Charts
            </h1>
            <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
              Highest rated movies by genre, ranked by community ratings
            </p>
          </header>

          {/* Genre selector */}
          {genres.length > 0 && (
            <div className="mb-10">
              <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 block">
                Genre
              </span>
              <div className="flex gap-2 flex-wrap">
                {genres.map((g) => (
                  <button
                    key={g}
                    onClick={() => setGenre(g)}
                    className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                      genre === g
                        ? "bg-primary-container text-on-primary-container shadow-md"
                        : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                    }`}
                  >
                    {g}
                  </button>
                ))}
              </div>
            </div>
          )}

          {loading && <LoadingSpinner text="Loading top charts..." />}
          {error && <ErrorPanel message={error} onRetry={() => genre && fetchTopCharts(genre)} />}

          {!loading && !error && genresLoaded && genre && results.length > 0 && (
            <>
              <p className="text-on-surface-variant text-sm mb-6">
                <span className="font-bold text-on-surface">{results.length}</span> top{" "}
                {genre} movie{results.length !== 1 ? "s" : ""}
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
                      onToggleBookmark={toggle} onAddToList={(id) => setAddToListMovieId(id)} isDismissed={isDismissed(item.movie.id)} onDismiss={toggleDismiss}
                      userRating={getRating(item.movie.id)}
                    />
                    <div className="mt-2 flex items-center gap-3 text-xs text-on-surface-variant font-medium">
                      <span>
                        <span className="material-symbols-outlined text-sm align-middle mr-1" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                        {item.avg_rating.toFixed(1)} avg
                      </span>
                      <span>
                        <span className="material-symbols-outlined text-sm align-middle mr-1">bar_chart</span>
                        {item.rating_count.toLocaleString()} rating{item.rating_count !== 1 ? "s" : ""}
                      </span>
                    </div>
                  </div>
                ))}
              </section>
            </>
          )}

          {!loading && !error && genresLoaded && genre && results.length === 0 && (
            <p className="text-center text-on-surface-variant text-lg py-20">
              No movies found for {genre} with enough ratings. Try another genre.
            </p>
          )}
        </div>
      </main>
      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
      <BottomNav />
    </>
  );
}
