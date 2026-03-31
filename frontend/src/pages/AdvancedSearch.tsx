import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { advancedSearchMovies, getGenres } from "../api/movies";
import type { AdvancedSearchResult, GenreCount } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useDismissed } from "../hooks/useDismissed";
import { useWatchlist } from "../hooks/useWatchlist";

const SORT_OPTIONS = [
  { value: "popularity", label: "Most Popular" },
  { value: "vote_average", label: "Highest Rated" },
  { value: "release_date", label: "Newest" },
  { value: "title", label: "Title A–Z" },
];

const DECADES = ["1950s", "1960s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s"];

const PAGE_SIZE = 20;

export default function AdvancedSearch() {
  const [params, setParams] = useSearchParams();

  // Derive filter state from URL params (single source of truth)
  const selectedGenre = params.get("genre") || null;
  const selectedDecade = params.get("decade") || null;
  const sortBy = params.get("sort_by") || "popularity";
  const offset = Number(params.get("offset")) || 0;

  // Text inputs: local state + debounced URL state
  const [directorInput, setDirectorInput] = useState(params.get("director") || "");
  const [keywordInput, setKeywordInput] = useState(params.get("keyword") || "");
  const [castInput, setCastInput] = useState(params.get("cast") || "");
  const [minRatingInput, setMinRatingInput] = useState(params.get("min_rating") || "");
  const [maxRatingInput, setMaxRatingInput] = useState(params.get("max_rating") || "");

  // Debounced values derived from URL
  const debouncedDirector = params.get("director") || "";
  const debouncedKeyword = params.get("keyword") || "";
  const debouncedCast = params.get("cast") || "";
  const debouncedMinRating = params.get("min_rating") || "";
  const debouncedMaxRating = params.get("max_rating") || "";

  const [genres, setGenres] = useState<GenreCount[]>([]);
  const [results, setResults] = useState<AdvancedSearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();

  // Helper: update URL params while preserving existing ones
  const updateParams = useCallback(
    (updates: Record<string, string | null>) => {
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
    },
    [setParams]
  );

  // Debounce text inputs — apply to URL after 600ms
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      updateParams({
        director: directorInput || null,
        keyword: keywordInput || null,
        cast: castInput || null,
        min_rating: minRatingInput || null,
        max_rating: maxRatingInput || null,
        offset: null,
      });
    }, 600);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [directorInput, keywordInput, castInput, minRatingInput, maxRatingInput]);

  // Load genres once
  useEffect(() => {
    getGenres()
      .then((data) => setGenres(data.genres))
      .catch(() => {});
  }, []);

  // Fetch results when any debounced filter or URL param changes
  useEffect(() => {
    setLoading(true);
    setError("");

    const parsedMin = debouncedMinRating ? Number(debouncedMinRating) : undefined;
    const parsedMax = debouncedMaxRating ? Number(debouncedMaxRating) : undefined;

    advancedSearchMovies({
      genre: selectedGenre ?? undefined,
      decade: selectedDecade ?? undefined,
      min_rating: parsedMin != null && parsedMin >= 0 ? parsedMin : undefined,
      max_rating: parsedMax != null && parsedMax >= 0 ? parsedMax : undefined,
      director: debouncedDirector || undefined,
      keyword: debouncedKeyword || undefined,
      cast: debouncedCast || undefined,
      sort_by: sortBy,
      offset,
      limit: PAGE_SIZE,
    })
      .then((data) => {
        setResults(data.results);
        setTotal(data.total);
        { const _ids = data.results.map((r) => r.movie.id); refreshForMovieIds(_ids); refreshDismissedForMovieIds(_ids); }
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  }, [selectedGenre, selectedDecade, sortBy, debouncedDirector, debouncedKeyword, debouncedCast, debouncedMinRating, debouncedMaxRating, offset]);

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  // Collect active filters for display
  const activeFilters: { key: string; label: string }[] = [];
  if (selectedGenre) activeFilters.push({ key: "genre", label: `Genre: ${selectedGenre}` });
  if (selectedDecade) activeFilters.push({ key: "decade", label: `Decade: ${selectedDecade}` });
  if (debouncedMinRating) activeFilters.push({ key: "min_rating", label: `Min Rating: ${debouncedMinRating}` });
  if (debouncedMaxRating) activeFilters.push({ key: "max_rating", label: `Max Rating: ${debouncedMaxRating}` });
  if (debouncedDirector) activeFilters.push({ key: "director", label: `Director: ${debouncedDirector}` });
  if (debouncedKeyword) activeFilters.push({ key: "keyword", label: `Keyword: ${debouncedKeyword}` });
  if (debouncedCast) activeFilters.push({ key: "cast", label: `Cast: ${debouncedCast}` });

  const clearAll = () => {
    setDirectorInput("");
    setKeywordInput("");
    setCastInput("");
    setMinRatingInput("");
    setMaxRatingInput("");
    setParams(new URLSearchParams());
  };

  const removeFilter = (key: string) => {
    if (key === "director") setDirectorInput("");
    if (key === "keyword") setKeywordInput("");
    if (key === "cast") setCastInput("");
    if (key === "min_rating") setMinRatingInput("");
    if (key === "max_rating") setMaxRatingInput("");
    updateParams({ [key]: null, offset: null });
  };

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <header className="mb-10">
            <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
              Advanced Search
            </h1>
            <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
              Combine multiple filters for precise discovery
            </p>
          </header>

          {/* Filter panel */}
          <div className="glass-panel p-6 rounded-2xl border border-outline-variant/10 mb-10 space-y-6">
            {/* Genre chips */}
            <div>
              <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 block">
                Genre
              </span>
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
            </div>

            {/* Decade pills */}
            <div>
              <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 block">
                Decade
              </span>
              <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                <button
                  onClick={() => updateParams({ decade: null, offset: null })}
                  className={`flex-shrink-0 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                    selectedDecade === null
                      ? "bg-primary-container text-on-primary-container shadow-md"
                      : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                  }`}
                >
                  All
                </button>
                {DECADES.map((d) => (
                  <button
                    key={d}
                    onClick={() => updateParams({ decade: d, offset: null })}
                    className={`flex-shrink-0 px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                      selectedDecade === d
                        ? "bg-primary-container text-on-primary-container shadow-md"
                        : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                    }`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            {/* Rating range + Sort + Clear */}
            <div className="flex flex-wrap gap-4 items-end">
              <div className="space-y-2">
                <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                  Min Rating
                </label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  step="0.5"
                  placeholder="e.g. 7"
                  value={minRatingInput}
                  onChange={(e) => setMinRatingInput(e.target.value)}
                  className="w-24 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm"
                />
              </div>

              <div className="space-y-2">
                <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                  Max Rating
                </label>
                <input
                  type="number"
                  min="0"
                  max="10"
                  step="0.5"
                  placeholder="e.g. 9"
                  value={maxRatingInput}
                  onChange={(e) => setMaxRatingInput(e.target.value)}
                  className="w-24 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm"
                />
              </div>

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

              {activeFilters.length > 0 && (
                <button
                  onClick={clearAll}
                  className="px-4 py-3 rounded-lg text-xs font-bold uppercase tracking-widest text-error hover:bg-error/10 transition-colors"
                >
                  Clear All
                </button>
              )}
            </div>

            {/* Text filter inputs: Director, Keyword, Cast */}
            <div className="flex flex-wrap gap-4">
              <div className="space-y-2 flex-1 min-w-[200px]">
                <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                  Director
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                    <span className="material-symbols-outlined text-outline text-lg">movie_filter</span>
                  </div>
                  <input
                    type="text"
                    placeholder="e.g. Nolan"
                    value={directorInput}
                    onChange={(e) => setDirectorInput(e.target.value)}
                    className="w-full pl-10 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm"
                  />
                </div>
              </div>

              <div className="space-y-2 flex-1 min-w-[200px]">
                <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                  Keyword
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                    <span className="material-symbols-outlined text-outline text-lg">sell</span>
                  </div>
                  <input
                    type="text"
                    placeholder="e.g. dystopia"
                    value={keywordInput}
                    onChange={(e) => setKeywordInput(e.target.value)}
                    className="w-full pl-10 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm"
                  />
                </div>
              </div>

              <div className="space-y-2 flex-1 min-w-[200px]">
                <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                  Cast
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                    <span className="material-symbols-outlined text-outline text-lg">theater_comedy</span>
                  </div>
                  <input
                    type="text"
                    placeholder="e.g. DiCaprio"
                    value={castInput}
                    onChange={(e) => setCastInput(e.target.value)}
                    className="w-full pl-10 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Active filter chips */}
          {activeFilters.length > 0 && (
            <div className="flex flex-wrap gap-2 mb-6">
              {activeFilters.map((f) => (
                <button
                  key={f.key}
                  onClick={() => removeFilter(f.key)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-primary-container/60 text-on-primary-container text-xs font-bold uppercase tracking-widest transition-all hover:bg-primary-container"
                >
                  {f.label}
                  <span className="material-symbols-outlined text-sm">close</span>
                </button>
              ))}
            </div>
          )}

          {/* Results */}
          {loading && <LoadingSpinner text="Searching..." />}
          {error && <ErrorPanel message={error} onRetry={() => updateParams({ offset: null })} />}

          {!loading && !error && (
            <>
              <p className="text-on-surface-variant text-sm mb-6">
                {total.toLocaleString()} movie{total !== 1 ? "s" : ""} found
              </p>
              <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
                {results.map((r) => (
                  <MovieCard key={r.movie.id} movie={r.movie} isBookmarked={isInWatchlist(r.movie.id)} onToggleBookmark={toggle} isDismissed={isDismissed(r.movie.id)} onDismiss={toggleDismiss} />
                ))}
              </section>

              {/* Pagination */}
              {totalPages > 1 && (
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

          {!loading && !error && results.length === 0 && (
            <p className="text-center text-on-surface-variant text-lg py-20">
              No movies match your filters. Try adjusting or removing some criteria.
            </p>
          )}
        </div>
      </main>
      <BottomNav />
    </>
  );
}
