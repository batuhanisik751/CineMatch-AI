import { useEffect, useRef, useState } from "react";
import {
  getActorFilmography,
  getPopularActors,
  searchActors,
} from "../api/movies";
import type {
  ActorFilmResult,
  ActorStats,
  ActorSummary,
} from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import AddToListModal from "../components/AddToListModal";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";
import { useDismissed } from "../hooks/useDismissed";
import { useWatchlist } from "../hooks/useWatchlist";

export default function Actors() {
  const { userId } = useUserId();
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  // Level 1 state (browse/search)
  const [actors, setActors] = useState<ActorSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  // Level 2 state (filmography)
  const [selectedActor, setSelectedActor] = useState<string | null>(null);
  const [filmography, setFilmography] = useState<ActorFilmResult[]>([]);
  const [stats, setStats] = useState<ActorStats | null>(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load popular actors on mount
  useEffect(() => {
    setLoading(true);
    getPopularActors(30)
      .then((data) => setActors(data.results))
      .catch((e) => setError(e.detail || e.message || "Failed to load actors"))
      .finally(() => setLoading(false));
  }, []);

  // Debounced search
  useEffect(() => {
    if (selectedActor !== null) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!searchQuery.trim()) {
      // Reset to popular actors
      setLoading(true);
      getPopularActors(30)
        .then((data) => setActors(data.results))
        .catch((e) => setError(e.detail || e.message || "Failed to load actors"))
        .finally(() => setLoading(false));
      return;
    }

    debounceRef.current = setTimeout(() => {
      setLoading(true);
      setError("");
      searchActors(searchQuery.trim(), 30)
        .then((data) => setActors(data.results))
        .catch((e) => setError(e.detail || e.message || "Search failed"))
        .finally(() => setLoading(false));
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery, selectedActor]);

  const handleSelectActor = (name: string) => {
    setSelectedActor(name);
    setLoading(true);
    setError("");
    getActorFilmography(name, userId)
      .then((data) => {
        setFilmography(data.filmography);
        setStats(data.stats);
        { const _ids = data.filmography.map((f) => f.movie.id); refreshForMovieIds(_ids); refreshDismissedForMovieIds(_ids); }
      })
      .catch((e) => setError(e.detail || e.message || "Failed to load filmography"))
      .finally(() => setLoading(false));
  };

  const handleBack = () => {
    setSelectedActor(null);
    setFilmography([]);
    setStats(null);
    setError("");
  };

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          {selectedActor === null ? (
            <>
              {/* Level 1: Browse/Search Actors */}
              <header className="mb-10">
                <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
                  Actor Filmography
                </h1>
                <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
                  Browse complete filmographies of your favorite actors
                </p>
              </header>

              {/* Search input */}
              <div className="mb-10">
                <div className="relative max-w-md">
                  <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-xl">
                    search
                  </span>
                  <input
                    type="text"
                    placeholder="Search actors..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 rounded-xl bg-surface-container-highest text-on-surface placeholder:text-on-surface-variant text-sm font-medium border border-white/5 focus:outline-none focus:border-[#FFC107]/50 transition-colors"
                  />
                </div>
              </div>

              {loading && <LoadingSpinner text="Loading actors..." />}
              {error && (
                <ErrorPanel
                  message={error}
                  onRetry={() => window.location.reload()}
                />
              )}

              {!loading && !error && actors.length > 0 && (
                <>
                  <p className="text-on-surface-variant text-sm mb-6">
                    {searchQuery.trim()
                      ? `${actors.length} result${actors.length !== 1 ? "s" : ""} for "${searchQuery}"`
                      : "Popular actors"}
                  </p>
                  <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                    {actors.map((a) => (
                      <button
                        key={a.name}
                        onClick={() => handleSelectActor(a.name)}
                        className="glass-card rounded-2xl p-6 text-left hover:bg-surface-container-high transition-all hover:scale-[1.03] duration-200 group"
                      >
                        <div className="w-12 h-12 rounded-full bg-[#FFC107]/10 flex items-center justify-center mb-3">
                          <span className="material-symbols-outlined text-[#FFC107] text-2xl">
                            theater_comedy
                          </span>
                        </div>
                        <h2 className="font-headline font-bold text-sm md:text-base text-on-surface group-hover:text-[#FFC107] transition-colors line-clamp-2">
                          {a.name}
                        </h2>
                        <div className="mt-2 space-y-1">
                          <p className="text-on-surface-variant text-xs font-bold uppercase tracking-widest">
                            {a.film_count} film{a.film_count !== 1 ? "s" : ""}
                          </p>
                          <p className="text-on-surface-variant text-xs">
                            <span
                              className="material-symbols-outlined text-sm align-middle mr-1"
                              style={{
                                fontVariationSettings: "'FILL' 1",
                              }}
                            >
                              star
                            </span>
                            {a.avg_vote.toFixed(1)} avg
                          </p>
                        </div>
                      </button>
                    ))}
                  </section>
                </>
              )}

              {!loading && !error && actors.length === 0 && (
                <p className="text-center text-on-surface-variant text-lg py-20">
                  No actors found
                  {searchQuery.trim() ? ` for "${searchQuery}"` : ""}. Try a
                  different search.
                </p>
              )}
            </>
          ) : (
            <>
              {/* Level 2: Filmography */}
              <header className="mb-10">
                <button
                  onClick={handleBack}
                  className="flex items-center gap-1 text-on-surface-variant hover:text-on-surface text-sm font-medium mb-4 transition-colors"
                >
                  <span className="material-symbols-outlined text-lg">
                    arrow_back
                  </span>
                  All Actors
                </button>
                <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
                  {selectedActor}
                </h1>

                {/* Stats bar */}
                {stats && (
                  <div className="flex flex-wrap items-center gap-4 mt-4">
                    <span className="glass-card rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                      {stats.total_films} film
                      {stats.total_films !== 1 ? "s" : ""}
                    </span>
                    <span className="glass-card rounded-lg px-3 py-1.5 text-xs font-bold text-on-surface-variant">
                      <span
                        className="material-symbols-outlined text-sm align-middle mr-1"
                        style={{ fontVariationSettings: "'FILL' 1" }}
                      >
                        star
                      </span>
                      {stats.avg_vote.toFixed(1)} avg
                    </span>
                    {stats.user_rated_count > 0 && stats.user_avg_rating != null && (
                      <span className="glass-card rounded-lg px-3 py-1.5 text-xs font-bold text-[#FFC107]">
                        <span className="material-symbols-outlined text-sm align-middle mr-1">
                          person
                        </span>
                        Your avg: {stats.user_avg_rating.toFixed(1)} ({stats.user_rated_count} rated)
                      </span>
                    )}
                    {stats.genres.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {stats.genres.map((g) => (
                          <span
                            key={g}
                            className="bg-surface-container-highest text-on-surface-variant rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-widest"
                          >
                            {g}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </header>

              {loading && (
                <LoadingSpinner
                  text={`Loading ${selectedActor}'s filmography...`}
                />
              )}
              {error && (
                <ErrorPanel
                  message={error}
                  onRetry={() => handleSelectActor(selectedActor)}
                />
              )}

              {!loading && !error && filmography.length > 0 && (
                <>
                  <p className="text-on-surface-variant text-sm mb-6">
                    Filmography sorted by release date
                  </p>
                  <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
                    {filmography.map((item) => (
                      <div key={item.movie.id}>
                        <MovieCard
                          movie={item.movie}
                          isBookmarked={isInWatchlist(item.movie.id)}
                          onToggleBookmark={toggle} onAddToList={(id) => setAddToListMovieId(id)} isDismissed={isDismissed(item.movie.id)} onDismiss={toggleDismiss}
                        />
                        <div className="mt-2 flex items-center gap-3 text-xs font-medium">
                          {item.user_rating != null ? (
                            <span className="text-[#FFC107]">
                              <span
                                className="material-symbols-outlined text-sm align-middle mr-1"
                                style={{
                                  fontVariationSettings: "'FILL' 1",
                                }}
                              >
                                star
                              </span>
                              Your rating: {item.user_rating}
                            </span>
                          ) : (
                            <span className="text-on-surface-variant">
                              <span className="material-symbols-outlined text-sm align-middle mr-1">
                                star
                              </span>
                              Not rated
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </section>
                </>
              )}

              {!loading && !error && filmography.length === 0 && (
                <p className="text-center text-on-surface-variant text-lg py-20">
                  No movies found for {selectedActor}.{" "}
                  <button
                    onClick={handleBack}
                    className="text-[#FFC107] underline"
                  >
                    Go back
                  </button>
                  .
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
