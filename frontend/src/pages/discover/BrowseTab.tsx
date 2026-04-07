import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { discoverMovies, getGenres, getLanguages, searchMovies } from "../../api/movies";
import type { GenreCount, LanguageCount, MovieSummary } from "../../api/types";
import { languageName } from "../../constants/languages";
import ErrorPanel from "../../components/ErrorPanel";
import LoadingSpinner from "../../components/LoadingSpinner";
import MovieCard from "../../components/MovieCard";
import AddToListModal from "../../components/AddToListModal";
import { useDismissed } from "../../hooks/useDismissed";
import { useRated } from "../../hooks/useRated";
import { useMatchPredictions } from "../../hooks/useMatchPredictions";
import { useWatchlist } from "../../hooks/useWatchlist";

const SORT_OPTIONS = [
  { value: "popularity", label: "Most Popular" },
  { value: "vote_average", label: "Highest Rated" },
  { value: "release_date", label: "Newest" },
  { value: "title", label: "Title A\u2013Z" },
];

const PAGE_SIZE = 20;

export default function BrowseTab() {
  const [params, setParams] = useSearchParams();

  // Derive filter state from URL params (single source of truth for back-nav)
  const selectedGenre = params.get("genre") || null;
  const sortBy = params.get("sort_by") || "popularity";
  const offset = Number(params.get("offset")) || 0;
  const searchMode: "title" | "vibe" = (params.get("mode") as "title" | "vibe") || "title";
  const searchQuery = params.get("q") || "";
  const selectedLanguage = params.get("language") || null;

  const [genres, setGenres] = useState<GenreCount[]>([]);
  const [languages, setLanguages] = useState<LanguageCount[]>([]);
  const [yearMin, setYearMin] = useState(params.get("year_min") || "");
  const [yearMax, setYearMax] = useState(params.get("year_max") || "");
  const [debouncedYearMin, setDebouncedYearMin] = useState(params.get("year_min") || "");
  const [debouncedYearMax, setDebouncedYearMax] = useState(params.get("year_max") || "");
  const [minRuntimeInput, setMinRuntimeInput] = useState(params.get("min_runtime") || "");
  const [maxRuntimeInput, setMaxRuntimeInput] = useState(params.get("max_runtime") || "");
  const [debouncedMinRuntime, setDebouncedMinRuntime] = useState(params.get("min_runtime") || "");
  const [debouncedMaxRuntime, setDebouncedMaxRuntime] = useState(params.get("max_runtime") || "");
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
  const runtimeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const { getMatchPercent, fetchMatchPercents } = useMatchPredictions();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

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

  // Debounce runtime inputs — only apply after 600ms of no typing
  useEffect(() => {
    if (runtimeTimerRef.current) clearTimeout(runtimeTimerRef.current);
    runtimeTimerRef.current = setTimeout(() => {
      setDebouncedMinRuntime(minRuntimeInput);
      setDebouncedMaxRuntime(maxRuntimeInput);
      updateParams({ min_runtime: minRuntimeInput || null, max_runtime: maxRuntimeInput || null });
    }, 600);
    return () => {
      if (runtimeTimerRef.current) clearTimeout(runtimeTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [minRuntimeInput, maxRuntimeInput]);

  // Load genres and languages once
  useEffect(() => {
    getGenres()
      .then((data) => setGenres(data.genres))
      .catch(() => {});
    getLanguages()
      .then((data) => setLanguages(data.languages))
      .catch(() => {});
  }, []);

  // Fetch movies — search mode vs browse mode
  useEffect(() => {
    setLoading(true);
    setError("");

    if (searchQuery.trim()) {
      // Search mode: title search only (vibe search disabled)
      const searchPromise = searchMovies(searchQuery.trim(), 40);

      searchPromise
        .then((data) => {
          setMovies(data.results);
          setTotal(data.total);
          const ids = data.results.map((m) => m.id);
          refreshForMovieIds(ids);
          refreshDismissedForMovieIds(ids);
          refreshRatingsForMovieIds(ids);
          fetchMatchPercents(ids);
        })
        .catch((e) => setError(e.detail || e.message))
        .finally(() => setLoading(false));
    } else {
      // Browse mode: use discover API with filters
      const parsedMin = debouncedYearMin ? Number(debouncedYearMin) : undefined;
      const parsedMax = debouncedYearMax ? Number(debouncedYearMax) : undefined;
      const parsedMinRuntime = debouncedMinRuntime ? Number(debouncedMinRuntime) : undefined;
      const parsedMaxRuntime = debouncedMaxRuntime ? Number(debouncedMaxRuntime) : undefined;

      discoverMovies({
        genre: selectedGenre ?? undefined,
        year_min: parsedMin && parsedMin >= 1888 ? parsedMin : undefined,
        year_max: parsedMax && parsedMax >= 1888 ? parsedMax : undefined,
        language: selectedLanguage ?? undefined,
        min_runtime: parsedMinRuntime && parsedMinRuntime >= 1 ? parsedMinRuntime : undefined,
        max_runtime: parsedMaxRuntime && parsedMaxRuntime >= 1 ? parsedMaxRuntime : undefined,
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
          fetchMatchPercents(ids);
        })
        .catch((e) => setError(e.detail || e.message))
        .finally(() => setLoading(false));
    }
  }, [searchQuery, searchMode, selectedGenre, selectedLanguage, sortBy, debouncedYearMin, debouncedYearMax, debouncedMinRuntime, debouncedMaxRuntime, offset]);

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
          placeholder="Search by title..."
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

      {/* Search mode toggle hidden — vibe search unavailable */}

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

          {/* Sort + Language + Year filters */}
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
                Language
              </label>
              <div className="relative">
                <select
                  value={selectedLanguage || ""}
                  onChange={(e) => updateParams({ language: e.target.value || null, offset: null })}
                  className="bg-surface-container-lowest border-none rounded-lg p-3 pr-10 text-on-surface appearance-none focus:ring-2 focus:ring-surface-tint font-body text-sm"
                >
                  <option value="">All Languages</option>
                  {languages.map((l) => (
                    <option key={l.code} value={l.code}>
                      {languageName(l.code)} ({l.count.toLocaleString()})
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

          {/* Runtime filter — presets + custom range */}
          <div className="space-y-3">
            <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant block">
              Runtime
            </span>
            <div className="flex flex-wrap gap-2">
              {[
                { label: "Any Length", min: null, max: null },
                { label: "Quick Watch (<90min)", min: null, max: "90" },
                { label: "Standard (90\u2013150min)", min: "90", max: "150" },
                { label: "Epic (>150min)", min: "150", max: null },
              ].map((preset) => {
                const isActive =
                  (params.get("min_runtime") || null) === preset.min &&
                  (params.get("max_runtime") || null) === preset.max;
                return (
                  <button
                    key={preset.label}
                    onClick={() => {
                      setMinRuntimeInput(preset.min || "");
                      setMaxRuntimeInput(preset.max || "");
                      setDebouncedMinRuntime(preset.min || "");
                      setDebouncedMaxRuntime(preset.max || "");
                      updateParams({ min_runtime: preset.min, max_runtime: preset.max, offset: null });
                    }}
                    className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                      isActive
                        ? "bg-primary-container text-on-primary-container shadow-md"
                        : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                    }`}
                  >
                    {preset.label}
                  </button>
                );
              })}
            </div>
            <div className="flex gap-4 items-end">
              <div className="space-y-2">
                <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                  Min minutes
                </label>
                <input
                  type="number"
                  min="1"
                  placeholder="e.g. 60"
                  value={minRuntimeInput}
                  onChange={(e) => { setMinRuntimeInput(e.target.value); updateParams({ offset: null }); }}
                  className="w-28 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm"
                />
              </div>
              <div className="space-y-2">
                <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                  Max minutes
                </label>
                <input
                  type="number"
                  min="1"
                  placeholder="e.g. 150"
                  value={maxRuntimeInput}
                  onChange={(e) => { setMaxRuntimeInput(e.target.value); updateParams({ offset: null }); }}
                  className="w-28 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm"
                />
              </div>
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
                Found <span className="font-bold text-on-surface">{total}</span> result{total !== 1 ? "s" : ""} for "<span className="italic text-primary">{searchQuery.trim()}</span>"
              </>
            ) : (
              <>{total.toLocaleString()} movie{total !== 1 ? "s" : ""} found</>
            )}
          </p>
          <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
            {movies.map((movie) => (
              <MovieCard key={movie.id} movie={movie} isBookmarked={isInWatchlist(movie.id)} onToggleBookmark={toggle} onAddToList={(id) => setAddToListMovieId(id)} isDismissed={isDismissed(movie.id)} onDismiss={toggleDismiss} userRating={getRating(movie.id)} matchPercent={getMatchPercent(movie.id)} />
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
      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
    </>
  );
}
