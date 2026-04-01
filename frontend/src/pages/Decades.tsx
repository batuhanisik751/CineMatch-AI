import { useEffect, useState } from "react";
import { getDecadeMovies, getDecades, getGenres } from "../api/movies";
import type { DecadeMovieResult, DecadeSummary } from "../api/types";
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

export default function Decades() {
  const [decades, setDecades] = useState<DecadeSummary[]>([]);
  const [selectedDecade, setSelectedDecade] = useState<number | null>(null);
  const [results, setResults] = useState<DecadeMovieResult[]>([]);
  const [total, setTotal] = useState(0);
  const [genre, setGenre] = useState<string | null>(null);
  const [genres, setGenres] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  // Load decades on mount
  useEffect(() => {
    setLoading(true);
    getDecades()
      .then((data) => setDecades(data.decades))
      .catch((e) => setError(e.detail || e.message || "Failed to load decades"))
      .finally(() => setLoading(false));
  }, []);

  // Load genres once (for filter pills)
  useEffect(() => {
    getGenres()
      .then((data) => setGenres(data.genres.map((g) => g.genre)))
      .catch(() => {});
  }, []);

  // Fetch movies when decade or genre changes
  const fetchDecadeMovies = (decade: number, g: string | null) => {
    setLoading(true);
    setError("");
    getDecadeMovies(decade, { genre: g ?? undefined, limit: 40 })
      .then((data) => {
        setResults(data.results);
        setTotal(data.total);
        { const _ids = data.results.map((r) => r.movie.id); refreshForMovieIds(_ids); refreshDismissedForMovieIds(_ids); refreshRatingsForMovieIds(_ids); }
      })
      .catch((e) => setError(e.detail || e.message || "Failed to load movies"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (selectedDecade !== null) {
      fetchDecadeMovies(selectedDecade, genre);
    }
  }, [selectedDecade, genre]);

  const handleSelectDecade = (decade: number) => {
    setGenre(null);
    setSelectedDecade(decade);
  };

  const handleBack = () => {
    setSelectedDecade(null);
    setResults([]);
    setGenre(null);
    setError("");
  };

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          {selectedDecade === null ? (
            <>
              {/* Timeline view */}
              <header className="mb-10">
                <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
                  Decade Explorer
                </h1>
                <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
                  Browse film history by era
                </p>
              </header>

              {loading && <LoadingSpinner text="Loading decades..." />}
              {error && <ErrorPanel message={error} onRetry={() => window.location.reload()} />}

              {!loading && !error && decades.length > 0 && (
                <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                  {decades.map((d) => (
                    <button
                      key={d.decade}
                      onClick={() => handleSelectDecade(d.decade)}
                      className="glass-card rounded-2xl p-6 text-left hover:bg-surface-container-high transition-all hover:scale-[1.03] duration-200 group"
                    >
                      <h2 className="font-headline font-extrabold text-2xl md:text-3xl text-on-surface group-hover:text-[#FFC107] transition-colors">
                        {d.decade}s
                      </h2>
                      <div className="mt-3 space-y-1">
                        <p className="text-on-surface-variant text-xs font-bold uppercase tracking-widest">
                          {d.movie_count.toLocaleString()} movies
                        </p>
                        <p className="text-on-surface-variant text-xs">
                          <span className="material-symbols-outlined text-sm align-middle mr-1" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                          {d.avg_rating.toFixed(1)} avg
                        </p>
                      </div>
                    </button>
                  ))}
                </section>
              )}
            </>
          ) : (
            <>
              {/* Decade detail view */}
              <header className="mb-10">
                <button
                  onClick={handleBack}
                  className="flex items-center gap-1 text-on-surface-variant hover:text-on-surface text-sm font-medium mb-4 transition-colors"
                >
                  <span className="material-symbols-outlined text-lg">arrow_back</span>
                  All Decades
                </button>
                <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
                  Best of the {selectedDecade}s
                </h1>
                <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
                  Top rated movies from {selectedDecade} to {selectedDecade + 9}, ranked by community ratings
                </p>
              </header>

              {/* Genre filter */}
              {genres.length > 0 && (
                <div className="mb-10">
                  <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 block">
                    Genre
                  </span>
                  <div className="flex gap-2 flex-wrap">
                    <button
                      onClick={() => setGenre(null)}
                      className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                        genre === null
                          ? "bg-primary-container text-on-primary-container shadow-md"
                          : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                      }`}
                    >
                      All
                    </button>
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

              {loading && <LoadingSpinner text={`Loading ${selectedDecade}s movies...`} />}
              {error && (
                <ErrorPanel
                  message={error}
                  onRetry={() => fetchDecadeMovies(selectedDecade, genre)}
                />
              )}

              {!loading && !error && results.length > 0 && (
                <>
                  <p className="text-on-surface-variant text-sm mb-6">
                    <span className="font-bold text-on-surface">{total}</span> movie
                    {total !== 1 ? "s" : ""} found
                    {genre ? ` in ${genre}` : ""}
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

              {!loading && !error && results.length === 0 && (
                <p className="text-center text-on-surface-variant text-lg py-20">
                  No movies found for the {selectedDecade}s{genre ? ` in ${genre}` : ""} with enough ratings.
                  {genre ? " Try another genre or " : " Try "}
                  <button onClick={handleBack} className="text-[#FFC107] underline">
                    another decade
                  </button>.
                </p>
              )}
            </>
          )}
        </div>
      </main>
      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
      <BottomNav />
    </>
  );
}
