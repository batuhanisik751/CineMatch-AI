import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { discoverMovies, getGenres, searchMovies, semanticSearchMovies } from "../api/movies";
import type { GenreCount, MovieSummary } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useDismissed } from "../hooks/useDismissed";
import { useRated } from "../hooks/useRated";
import { useWatchlist } from "../hooks/useWatchlist";

const SORT_OPTIONS = [
  { value: "popularity", label: "Most Popular" },
  { value: "vote_average", label: "Highest Rated" },
  { value: "release_date", label: "Newest" },
  { value: "title", label: "Title A–Z" },
];

const PAGE_SIZE = 20;

export default function Discover() {
  const [params, setParams] = useSearchParams();

  // Derive filter state from URL params (single source of truth for back-nav)
  const selectedGenre = params.get("genre") || null;
  const sortBy = params.get("sort_by") || "popularity";
  const offset = Number(params.get("offset")) || 0;
  const searchMode: "title" | "vibe" = (params.get("mode") as "title" | "vibe") || "title";
  const searchQuery = params.get("q") || "";

  const [genres, setGenres] = useState<GenreCount[]>([]);
  const [yearMin, setYearMin] = useState(params.get("year_min") || "");
  const [yearMax, setYearMax] = useState(params.get("year_max") || "");
  const [debouncedYearMin, setDebouncedYearMin] = useState(params.get("year_min") || "");
  const [debouncedYearMax, setDebouncedYearMax] = useState(params.get("year_max") || "");
  const [movies, setMovies] = useState<MovieSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Helper: update URL params while preserving existing ones
  const updateParams = (updates: Record<string, string | null>) => {
    setParams((prev) => {
      const next = new URLSearchParams(prev);
      for (const [key, value] of Object.entries(updates)) {
        if (value === null || value === "" || value === "0") {
          next.delete(key);
        } else {
          next.set(key, value);
        }
      }
      return next;
    });
  };

  const yearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();

  // Debounce year inputs — only apply after 600ms of no typing
  useEffect(() => {
    if (yearTimerRef.current) clearTimeout(yearTimerRef.current);
    yearTimerRef.current = setTimeout(() => {
      setDebouncedYearMin(yearMin);
      setDebouncedYearMax(yearMax);
      updateParams({ year_min: yearMin || null, year_max: yearMax || null });
    }, 600);
    return () => {
      if (yearTimerRef.current) clearTimeout(yearTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [yearMin, yearMax]);

  // Load genres once
  useEffect(() => {
    getGenres()
      .then((data) => setGenres(data.genres))
      .catch(() => {});
  }, []);

  // Fetch movies — search mode vs browse mode
  useEffect(() => {
    setLoading(true);
    setError("");

    if (searchQuery.trim()) {
      // Search mode: title search or semantic vibe search
      const searchPromise =
        searchMode === "vibe"
          ? semanticSearchMovies(searchQuery.trim(), 40).then((data) => ({
              results: data.results.map((r) => r.movie),
              total: data.total,
            }))
          : searchMovies(searchQuery.trim(), 40);

      searchPromise
        .then((data) => {
          setMovies(data.results);
          setTotal(data.total);
          const ids = data.results.map((m) => m.id);
          refreshForMovieIds(ids);
          refreshDismissedForMovieIds(ids);
          refreshRatingsForMovieIds(ids);
        })
        .catch((e) => setError(e.detail || e.message))
        .finally(() => setLoading(false));
    } else {
      // Browse mode: use discover API with filters
      const parsedMin = debouncedYearMin ? Number(debouncedYearMin) : undefined;
      const parsedMax = debouncedYearMax ? Number(debouncedYearMax) : undefined;

      discoverMovies({
        genre: selectedGenre ?? undefined,
        year_min: parsedMin && parsedMin >= 1888 ? parsedMin : undefined,
        year_max: parsedMax && parsedMax >= 1888 ? parsedMax : undefined,
        sort_by: sortBy,
        offset,
        limit: PAGE_SIZE,
      })
        .then((data) => {
          setMovies(data.results);
          setTotal(data.total);
          const ids = data.results.map((m) => m.id);
          refreshForMovieIds(ids);
          refreshDismissedForMovieIds(ids);
          refreshRatingsForMovieIds(ids);
        })
        .catch((e) => setError(e.detail || e.message))
        .finally(() => setLoading(false));
    }
  }, [searchQuery, searchMode, selectedGenre, sortBy, debouncedYearMin, debouncedYearMax, offset]);

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const isSearchMode = searchQuery.trim().length > 0;

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateParams({ offset: null });
  };

  const clearSearch = () => {
    updateParams({ q: null, mode: null, offset: null });
  };

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <header className="mb-10">
            <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
              Discover
            </h1>
            <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
              Search and browse the full catalog
            </p>
          </header>

          {/* Search bar */}
          <form onSubmit={handleSearchSubmit} className="relative mb-8">
            <div className="absolute inset-y-0 left-5 flex items-center pointer-events-none">
              <span className="material-symbols-outlined text-outline">search</span>
            </div>
            <input
              value={searchQuery}
              onChange={(e) => updateParams({ q: e.target.value, offset: null })}
              className="w-full h-14 pl-14 pr-12 bg-surface-container-lowest border-none rounded-xl text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint shadow-lg transition-all duration-300 font-body text-base"
              placeholder={searchMode === "vibe" ? "Describe a movie vibe..." : "Search by title..."}
              type="text"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={clearSearch}
                className="absolute inset-y-0 right-4 flex items-center text-outline hover:text-on-surface transition-colors"
              >
                <span className="material-symbols-outlined text-xl">close</span>
              </button>
            )}
          </form>

          {/* Search mode toggle */}
          <div className="flex gap-2 mb-8">
            <button
              onClick={() => updateParams({ mode: null, offset: null })}
              className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                searchMode === "title"
                  ? "bg-primary-container text-on-primary-container shadow-md"
                  : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
              }`}
            >
              Search by title
            </button>
            <button
              onClick={() => updateParams({ mode: "vibe", offset: null })}
              className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                searchMode === "vibe"
                  ? "bg-primary-container text-on-primary-container shadow-md"
                  : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
              }`}
            >
              Search by vibe
            </button>
          </div>

          {/* Filters — hidden during search mode */}
          {!isSearchMode && (
            <div className="glass-panel p-6 rounded-2xl border border-outline-variant/10 mb-10 space-y-6">
              {/* Genre chips */}
              <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                <button
                  onClick={() => updateParams({ genre: null, offset: null })}
                  className={`flex-shrink-0 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                    selectedGenre === null
                      ? "bg-primary-container text-on-primary-container shadow-md"
                      : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                  }`}
                >
                  All
                </button>
                {genres.map((g) => (
                  <button
                    key={g.genre}
                    onClick={() => updateParams({ genre: g.genre, offset: null })}
                    className={`flex-shrink-0 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                      selectedGenre === g.genre
                        ? "bg-primary-container text-on-primary-container shadow-md"
                        : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                    }`}
                  >
                    {g.genre}
                  </button>
                ))}
              </div>

              {/* Sort + Year filters */}
              <div className="flex flex-wrap gap-4 items-end">
                <div className="space-y-2">
                  <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                    Sort by
                  </label>
                  <div className="relative">
                    <select
                      value={sortBy}
                      onChange={(e) => updateParams({ sort_by: e.target.value, offset: null })}
                      className="bg-surface-container-lowest border-none rounded-lg p-3 pr-10 text-on-surface appearance-none focus:ring-2 focus:ring-surface-tint font-body text-sm"
                    >
                      {SORT_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>
                          {opt.label}
                        </option>
                      ))}
                    </select>
                    <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none">
                      <span className="material-symbols-outlined text-outline text-sm">expand_more</span>
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                    Year from
                  </label>
                  <input
                    type="number"
                    min="1888"
                    max="2030"
                    placeholder="e.g. 2000"
                    value={yearMin}
                    onChange={(e) => { setYearMin(e.target.value); updateParams({ offset: null }); }}
                    className="w-28 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm"
                  />
                </div>

                <div className="space-y-2">
                  <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                    Year to
                  </label>
                  <input
                    type="number"
                    min="1888"
                    max="2030"
                    placeholder="e.g. 2024"
                    value={yearMax}
                    onChange={(e) => { setYearMax(e.target.value); updateParams({ offset: null }); }}
                    className="w-28 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Results */}
          {loading && <LoadingSpinner text={isSearchMode ? "Searching..." : "Loading movies..."} />}
          {error && <ErrorPanel message={error} onRetry={() => updateParams({ offset: null })} />}

          {!loading && !error && (
            <>
              <p className="text-on-surface-variant text-sm mb-6">
                {isSearchMode ? (
                  <>
                    Found <span className="font-bold text-on-surface">{total}</span> {searchMode === "vibe" ? "vibe match" : "result"}{total !== 1 ? (searchMode === "vibe" ? "es" : "s") : ""} for "<span className="italic text-primary">{searchQuery.trim()}</span>"
                  </>
                ) : (
                  <>{total.toLocaleString()} movie{total !== 1 ? "s" : ""} found</>
                )}
              </p>
              <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
                {movies.map((movie) => (
                  <MovieCard key={movie.id} movie={movie} isBookmarked={isInWatchlist(movie.id)} onToggleBookmark={toggle} isDismissed={isDismissed(movie.id)} onDismiss={toggleDismiss} userRating={getRating(movie.id)} />
                ))}
              </section>

              {/* Pagination — only for browse mode */}
              {!isSearchMode && totalPages > 1 && (
                <div className="flex items-center justify-center gap-4 mt-12">
                  <button
                    onClick={() => updateParams({ offset: String(Math.max(0, offset - PAGE_SIZE)) })}
                    disabled={offset === 0}
                    className="px-5 py-2.5 bg-surface-container-highest text-on-surface rounded-lg font-headline text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-container-high transition-colors"
                  >
                    Previous
                  </button>
                  <span className="text-on-surface-variant text-sm font-body">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => updateParams({ offset: String(offset + PAGE_SIZE) })}
                    disabled={offset + PAGE_SIZE >= total}
                    className="px-5 py-2.5 bg-surface-container-highest text-on-surface rounded-lg font-headline text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-container-high transition-colors"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}

          {!loading && !error && movies.length === 0 && (
            <p className="text-center text-on-surface-variant text-lg py-20">
              {isSearchMode
                ? "No movies found. Try a different search."
                : "No movies match your filters. Try adjusting them."}
            </p>
          )}
        </div>
      </main>
      <BottomNav />
    </>
  );
}
