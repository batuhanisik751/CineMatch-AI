import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { discoverMovies, getGenres, searchMovies } from "../api/movies";
import type { GenreCount, MovieSummary } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";

const SORT_OPTIONS = [
  { value: "popularity", label: "Most Popular" },
  { value: "vote_average", label: "Highest Rated" },
  { value: "release_date", label: "Newest" },
  { value: "title", label: "Title A–Z" },
];

const PAGE_SIZE = 20;

export default function Discover() {
  const [params, setParams] = useSearchParams();

  const [genres, setGenres] = useState<GenreCount[]>([]);
  const [selectedGenre, setSelectedGenre] = useState<string | null>(null);
  const [sortBy, setSortBy] = useState(params.get("sort_by") || "popularity");
  const [yearMin, setYearMin] = useState("");
  const [yearMax, setYearMax] = useState("");
  const [debouncedYearMin, setDebouncedYearMin] = useState("");
  const [debouncedYearMax, setDebouncedYearMax] = useState("");
  const [searchQuery, setSearchQuery] = useState(params.get("q") || "");
  const [movies, setMovies] = useState<MovieSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const yearTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounce year inputs — only apply after 600ms of no typing
  useEffect(() => {
    if (yearTimerRef.current) clearTimeout(yearTimerRef.current);
    yearTimerRef.current = setTimeout(() => {
      setDebouncedYearMin(yearMin);
      setDebouncedYearMax(yearMax);
    }, 600);
    return () => {
      if (yearTimerRef.current) clearTimeout(yearTimerRef.current);
    };
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
      // Search mode: use title search API
      searchMovies(searchQuery.trim(), 40)
        .then((data) => {
          setMovies(data.results);
          setTotal(data.total);
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
        })
        .catch((e) => setError(e.detail || e.message))
        .finally(() => setLoading(false));
    }
  }, [searchQuery, selectedGenre, sortBy, debouncedYearMin, debouncedYearMax, offset]);

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const isSearchMode = searchQuery.trim().length > 0;

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setOffset(0);
    // Update URL params for shareability
    if (searchQuery.trim()) {
      setParams({ q: searchQuery.trim() });
    } else {
      setParams({});
    }
  };

  const clearSearch = () => {
    setSearchQuery("");
    setOffset(0);
    setParams({});
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
              onChange={(e) => { setSearchQuery(e.target.value); setOffset(0); }}
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

          {/* Filters — hidden during search mode */}
          {!isSearchMode && (
            <div className="glass-panel p-6 rounded-2xl border border-outline-variant/10 mb-10 space-y-6">
              {/* Genre chips */}
              <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
                <button
                  onClick={() => { setSelectedGenre(null); setOffset(0); }}
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
                    onClick={() => { setSelectedGenre(g.genre); setOffset(0); }}
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
                      onChange={(e) => { setSortBy(e.target.value); setOffset(0); }}
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
                    onChange={(e) => { setYearMin(e.target.value); setOffset(0); }}
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
                    onChange={(e) => { setYearMax(e.target.value); setOffset(0); }}
                    className="w-28 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Results */}
          {loading && <LoadingSpinner text={isSearchMode ? "Searching..." : "Loading movies..."} />}
          {error && <ErrorPanel message={error} onRetry={() => setOffset(0)} />}

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
                  <MovieCard key={movie.id} movie={movie} />
                ))}
              </section>

              {/* Pagination — only for browse mode */}
              {!isSearchMode && totalPages > 1 && (
                <div className="flex items-center justify-center gap-4 mt-12">
                  <button
                    onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                    disabled={offset === 0}
                    className="px-5 py-2.5 bg-surface-container-highest text-on-surface rounded-lg font-headline text-sm font-medium disabled:opacity-30 disabled:cursor-not-allowed hover:bg-surface-container-high transition-colors"
                  >
                    Previous
                  </button>
                  <span className="text-on-surface-variant text-sm font-body">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setOffset(offset + PAGE_SIZE)}
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
