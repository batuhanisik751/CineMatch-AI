import { useEffect, useRef, useState } from "react";
import {
  getKeywordMovies,
  getPopularKeywords,
  searchKeywords,
} from "../api/movies";
import type {
  KeywordMovieResult,
  KeywordStats,
  KeywordSummary,
} from "../api/types";
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

export default function Keywords() {
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  // Level 1 state (browse/search)
  const [keywords, setKeywords] = useState<KeywordSummary[]>([]);
  const [searchQuery, setSearchQuery] = useState("");

  // Level 2 state (keyword movies)
  const [selectedKeyword, setSelectedKeyword] = useState<string | null>(null);
  const [movies, setMovies] = useState<KeywordMovieResult[]>([]);
  const [stats, setStats] = useState<KeywordStats | null>(null);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load popular keywords on mount
  useEffect(() => {
    setLoading(true);
    getPopularKeywords(100)
      .then((data) => setKeywords(data.results))
      .catch((e) => setError(e.detail || e.message || "Failed to load keywords"))
      .finally(() => setLoading(false));
  }, []);

  // Debounced search
  useEffect(() => {
    if (selectedKeyword !== null) return;

    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!searchQuery.trim()) {
      setLoading(true);
      getPopularKeywords(100)
        .then((data) => setKeywords(data.results))
        .catch((e) => setError(e.detail || e.message || "Failed to load keywords"))
        .finally(() => setLoading(false));
      return;
    }

    debounceRef.current = setTimeout(() => {
      setLoading(true);
      setError("");
      searchKeywords(searchQuery.trim(), 50)
        .then((data) => setKeywords(data.results))
        .catch((e) => setError(e.detail || e.message || "Search failed"))
        .finally(() => setLoading(false));
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery, selectedKeyword]);

  const handleSelectKeyword = (keyword: string) => {
    setSelectedKeyword(keyword);
    setMovies([]);
    setOffset(0);
    setLoading(true);
    setError("");
    getKeywordMovies(keyword, { offset: 0, limit: 20 })
      .then((data) => {
        setMovies(data.results);
        setStats(data.stats);
        setTotal(data.total);
        { const _ids = data.results.map((r) => r.movie.id); refreshForMovieIds(_ids); refreshDismissedForMovieIds(_ids); refreshRatingsForMovieIds(_ids); }
      })
      .catch((e) => setError(e.detail || e.message || "Failed to load movies"))
      .finally(() => setLoading(false));
  };

  const handleLoadMore = () => {
    if (!selectedKeyword) return;
    const nextOffset = offset + 20;
    setOffset(nextOffset);
    setLoading(true);
    getKeywordMovies(selectedKeyword, { offset: nextOffset, limit: 20 })
      .then((data) => {
        setMovies((prev) => [...prev, ...data.results]);
        { const _ids = data.results.map((r) => r.movie.id); refreshForMovieIds(_ids); refreshDismissedForMovieIds(_ids); refreshRatingsForMovieIds(_ids); }
      })
      .catch((e) => setError(e.detail || e.message || "Failed to load more"))
      .finally(() => setLoading(false));
  };

  const handleBack = () => {
    setSelectedKeyword(null);
    setMovies([]);
    setStats(null);
    setTotal(0);
    setOffset(0);
    setError("");
  };

  // Compute font sizes for tag cloud
  const computeFontSize = (count: number) => {
    if (keywords.length === 0) return 14;
    const counts = keywords.map((k) => k.count);
    const minCount = Math.min(...counts);
    const maxCount = Math.max(...counts);
    const minSize = 12;
    const maxSize = 36;
    if (maxCount === minCount) return (minSize + maxSize) / 2;
    const minLog = Math.log(minCount);
    const maxLog = Math.log(maxCount);
    const scale = (Math.log(count) - minLog) / (maxLog - minLog);
    return minSize + scale * (maxSize - minSize);
  };

  const computeOpacity = (count: number) => {
    if (keywords.length === 0) return 0.8;
    const counts = keywords.map((k) => k.count);
    const minCount = Math.min(...counts);
    const maxCount = Math.max(...counts);
    if (maxCount === minCount) return 0.8;
    const scale = (count - minCount) / (maxCount - minCount);
    return 0.5 + scale * 0.5;
  };

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          {selectedKeyword === null ? (
            <>
              {/* Level 1: Tag Cloud Browse/Search */}
              <header className="mb-10">
                <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
                  Keyword Explorer
                </h1>
                <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
                  Discover movies by thematic tags
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
                    placeholder="Search keywords..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-3 rounded-xl bg-surface-container-highest text-on-surface placeholder:text-on-surface-variant text-sm font-medium border border-white/5 focus:outline-none focus:border-[#FFC107]/50 transition-colors"
                  />
                </div>
              </div>

              {loading && <LoadingSpinner text="Loading keywords..." />}
              {error && (
                <ErrorPanel
                  message={error}
                  onRetry={() => window.location.reload()}
                />
              )}

              {!loading && !error && keywords.length > 0 && (
                <>
                  <p className="text-on-surface-variant text-sm mb-6">
                    {searchQuery.trim()
                      ? `${keywords.length} result${keywords.length !== 1 ? "s" : ""} for "${searchQuery}"`
                      : "Popular keywords — click to explore"}
                  </p>

                  {searchQuery.trim() ? (
                    /* List view for search results */
                    <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                      {keywords.map((k) => (
                        <button
                          key={k.keyword}
                          onClick={() => handleSelectKeyword(k.keyword)}
                          className="glass-card rounded-2xl p-6 text-left hover:bg-surface-container-high transition-all hover:scale-[1.03] duration-200 group"
                        >
                          <div className="w-10 h-10 rounded-full bg-[#FFC107]/10 flex items-center justify-center mb-3">
                            <span className="material-symbols-outlined text-[#FFC107] text-xl">
                              sell
                            </span>
                          </div>
                          <h2 className="font-headline font-bold text-sm text-on-surface group-hover:text-[#FFC107] transition-colors line-clamp-2">
                            {k.keyword}
                          </h2>
                          <p className="text-on-surface-variant text-xs font-bold uppercase tracking-widest mt-2">
                            {k.count} movie{k.count !== 1 ? "s" : ""}
                          </p>
                        </button>
                      ))}
                    </section>
                  ) : (
                    /* Tag cloud view for popular keywords */
                    <section className="glass-card rounded-2xl p-8">
                      <div className="flex flex-wrap items-center justify-center gap-3">
                        {keywords.map((k) => (
                          <button
                            key={k.keyword}
                            onClick={() => handleSelectKeyword(k.keyword)}
                            className="hover:text-[#FFC107] transition-all duration-200 hover:scale-110 px-2 py-1 rounded-lg hover:bg-[#FFC107]/10"
                            style={{
                              fontSize: `${computeFontSize(k.count)}px`,
                              color: `rgba(255, 193, 7, ${computeOpacity(k.count)})`,
                              lineHeight: 1.4,
                            }}
                            title={`${k.keyword} (${k.count} movies)`}
                          >
                            {k.keyword}
                          </button>
                        ))}
                      </div>
                    </section>
                  )}
                </>
              )}

              {!loading && !error && keywords.length === 0 && (
                <p className="text-center text-on-surface-variant text-lg py-20">
                  No keywords found
                  {searchQuery.trim() ? ` for "${searchQuery}"` : ""}. Try a
                  different search.
                </p>
              )}
            </>
          ) : (
            <>
              {/* Level 2: Keyword Movies */}
              <header className="mb-10">
                <button
                  onClick={handleBack}
                  className="flex items-center gap-1 text-on-surface-variant hover:text-on-surface text-sm font-medium mb-4 transition-colors"
                >
                  <span className="material-symbols-outlined text-lg">
                    arrow_back
                  </span>
                  All Keywords
                </button>
                <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
                  {selectedKeyword}
                </h1>

                {/* Stats bar */}
                {stats && (
                  <div className="flex flex-wrap items-center gap-4 mt-4">
                    <span className="glass-card rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                      {stats.total_movies} movie
                      {stats.total_movies !== 1 ? "s" : ""}
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
                    {stats.top_genres.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {stats.top_genres.map((g) => (
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

              {loading && movies.length === 0 && (
                <LoadingSpinner
                  text={`Loading movies for "${selectedKeyword}"...`}
                />
              )}
              {error && (
                <ErrorPanel
                  message={error}
                  onRetry={() => handleSelectKeyword(selectedKeyword)}
                />
              )}

              {!error && movies.length > 0 && (
                <>
                  <p className="text-on-surface-variant text-sm mb-6">
                    Sorted by popularity
                  </p>
                  <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
                    {movies.map((item) => (
                      <MovieCard
                        key={item.movie.id}
                        movie={item.movie}
                        isBookmarked={isInWatchlist(item.movie.id)}
                        onToggleBookmark={toggle} onAddToList={(id) => setAddToListMovieId(id)} isDismissed={isDismissed(item.movie.id)} onDismiss={toggleDismiss}
                        userRating={getRating(item.movie.id)}
                      />
                    ))}
                  </section>

                  {/* Load more button */}
                  {movies.length < total && (
                    <div className="flex justify-center mt-10">
                      <button
                        onClick={handleLoadMore}
                        disabled={loading}
                        className="glass-card rounded-xl px-8 py-3 text-sm font-bold uppercase tracking-widest text-[#FFC107] hover:bg-[#FFC107]/10 transition-all disabled:opacity-50"
                      >
                        {loading ? "Loading..." : "Load More"}
                      </button>
                    </div>
                  )}
                </>
              )}

              {!loading && !error && movies.length === 0 && (
                <p className="text-center text-on-surface-variant text-lg py-20">
                  No movies found for "{selectedKeyword}".{" "}
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
