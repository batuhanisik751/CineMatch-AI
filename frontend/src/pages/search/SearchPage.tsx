import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { advancedSearchMovies, getGenres, getLanguages, searchMovies, semanticSearchMovies } from "../../api/movies";
import { getMoodRecommendations } from "../../api/recommendations";
import type { GenreCount, LanguageCount, MovieSummary } from "../../api/types";
import { languageName } from "../../constants/languages";
import { MOOD_PRESETS, type MoodPreset } from "../../constants/moods";
import ErrorPanel from "../../components/ErrorPanel";
import LoadingSpinner from "../../components/LoadingSpinner";
import MovieCard from "../../components/MovieCard";
import AddToListModal from "../../components/AddToListModal";
import { useDismissed } from "../../hooks/useDismissed";
import { useMatchPredictions } from "../../hooks/useMatchPredictions";
import { useRated } from "../../hooks/useRated";
import { useUserId } from "../../hooks/useUserId";
import { useWatchlist } from "../../hooks/useWatchlist";

const SORT_OPTIONS = [
  { value: "popularity", label: "Most Popular" },
  { value: "vote_average", label: "Highest Rated" },
  { value: "release_date", label: "Newest" },
  { value: "title", label: "Title A\u2013Z" },
];

const DECADES = ["1950s", "1960s", "1970s", "1980s", "1990s", "2000s", "2010s", "2020s"];

const PAGE_SIZE = 20;

type SearchMode = "idle" | "title" | "mood" | "advanced" | "combined";

interface UnifiedMovie {
  movie: MovieSummary;
  isPersonalized?: boolean;
}

export default function SearchPage() {
  const [params, setParams] = useSearchParams();
  const { userId } = useUserId();

  // --- Search bar state ---
  const q = params.get("q") || "";
  const [searchInput, setSearchInput] = useState(q);
  const searchDebounceRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => { setSearchInput(q); }, [q]);

  // --- Mood state ---
  const selectedMoodsParam = params.get("moods") || "";
  const selectedMoods = selectedMoodsParam ? new Set(selectedMoodsParam.split(",")) : new Set<string>();
  const [moodMovies, setMoodMovies] = useState<Map<string, { movies: MovieSummary[]; loading: boolean; isPersonalized: boolean }>>(new Map());
  const moodAbortControllers = useRef<Map<string, AbortController>>(new Map());
  const moodFallback = useRef(false);

  // --- Advanced filter state ---
  const [filtersOpen, setFiltersOpen] = useState(false);
  const selectedGenre = params.get("genre") || null;
  const selectedDecade = params.get("decade") || null;
  const sortBy = params.get("sort_by") || "popularity";
  const offset = Number(params.get("offset")) || 0;
  const selectedLanguage = params.get("language") || null;

  const [directorInput, setDirectorInput] = useState(params.get("director") || "");
  const [keywordInput, setKeywordInput] = useState(params.get("keyword") || "");
  const [castInput, setCastInput] = useState(params.get("cast") || "");
  const [minRatingInput, setMinRatingInput] = useState(params.get("min_rating") || "");
  const [maxRatingInput, setMaxRatingInput] = useState(params.get("max_rating") || "");
  const [minRuntimeInput, setMinRuntimeInput] = useState(params.get("min_runtime") || "");
  const [maxRuntimeInput, setMaxRuntimeInput] = useState(params.get("max_runtime") || "");

  const debouncedDirector = params.get("director") || "";
  const debouncedKeyword = params.get("keyword") || "";
  const debouncedCast = params.get("cast") || "";
  const debouncedMinRating = params.get("min_rating") || "";
  const debouncedMaxRating = params.get("max_rating") || "";
  const debouncedMinRuntime = params.get("min_runtime") || "";
  const debouncedMaxRuntime = params.get("max_runtime") || "";

  // --- Genres & Languages ---
  const [genres, setGenres] = useState<GenreCount[]>([]);
  const [languages, setLanguages] = useState<LanguageCount[]>([]);

  // --- Results state ---
  const [results, setResults] = useState<UnifiedMovie[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // --- Shared hooks ---
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const { getMatchPercent, fetchMatchPercents } = useMatchPredictions();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  // --- Filter text debounce ---
  const filterDebounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

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

  // --- Determine active advanced filters ---
  const hasAdvancedFilters = !!(
    selectedGenre || selectedDecade || debouncedDirector || debouncedKeyword ||
    debouncedCast || selectedLanguage || debouncedMinRating || debouncedMaxRating ||
    debouncedMinRuntime || debouncedMaxRuntime
  );

  const activeFilterCount = [
    selectedGenre, selectedDecade, debouncedDirector, debouncedKeyword,
    debouncedCast, selectedLanguage, debouncedMinRating, debouncedMaxRating,
    debouncedMinRuntime, debouncedMaxRuntime,
  ].filter(Boolean).length;

  // Auto-open filters if any are active from URL
  useEffect(() => {
    if (hasAdvancedFilters) setFiltersOpen(true);
  }, []);

  // --- Determine search mode ---
  const hasMoods = selectedMoods.size > 0;
  const hasQuery = !!q;

  const searchMode: SearchMode =
    !hasQuery && !hasMoods && !hasAdvancedFilters ? "idle" :
    hasMoods && !hasQuery && !hasAdvancedFilters ? "mood" :
    hasQuery && !hasMoods && !hasAdvancedFilters ? "title" :
    !hasQuery && !hasMoods && hasAdvancedFilters ? "advanced" :
    "combined";

  // --- Search bar handler ---
  const handleSearchInput = (value: string) => {
    setSearchInput(value);
    clearTimeout(searchDebounceRef.current);
    searchDebounceRef.current = setTimeout(() => {
      updateParams({ q: value.trim() || null, offset: null });
    }, 500);
  };

  // --- Mood handlers ---
  const toggleMood = (mood: MoodPreset) => {
    const next = new Set(selectedMoods);
    if (next.has(mood.label)) {
      next.delete(mood.label);
      // Clean up mood movies
      moodAbortControllers.current.get(mood.label)?.abort();
      moodAbortControllers.current.delete(mood.label);
      setMoodMovies((prev) => {
        const m = new Map(prev);
        m.delete(mood.label);
        return m;
      });
    } else {
      next.add(mood.label);
      fetchMoodResults(mood.query, mood.label);
    }
    const moodsStr = [...next].join(",");
    updateParams({ moods: moodsStr || null, offset: null });
  };

  const fetchMoodResults = (query: string, label: string) => {
    moodAbortControllers.current.get(label)?.abort();
    const controller = new AbortController();
    moodAbortControllers.current.set(label, controller);

    setMoodMovies((prev) => {
      const m = new Map(prev);
      m.set(label, { movies: [], loading: true, isPersonalized: false });
      return m;
    });

    const applyResults = (movies: MovieSummary[], personalized: boolean) => {
      if (controller.signal.aborted) return;
      setMoodMovies((prev) => {
        const m = new Map(prev);
        m.set(label, { movies, loading: false, isPersonalized: personalized });
        return m;
      });
      const ids = movies.map((mv) => mv.id);
      refreshForMovieIds(ids);
      refreshDismissedForMovieIds(ids);
      refreshRatingsForMovieIds(ids);
      fetchMatchPercents(ids);
    };

    const fallbackToSemantic = () =>
      semanticSearchMovies(query, 20).then((data) =>
        applyResults(data.results.map((r) => r.movie), false)
      );

    const request = !moodFallback.current && userId
      ? getMoodRecommendations({ mood: query, user_id: userId })
          .then((data) => applyResults(data.results.map((r) => r.movie), data.is_personalized))
          .catch(() => {
            moodFallback.current = true;
            return fallbackToSemantic();
          })
      : fallbackToSemantic();

    request.catch(() => {
      if (!controller.signal.aborted) {
        setMoodMovies((prev) => {
          const m = new Map(prev);
          m.set(label, { movies: [], loading: false, isPersonalized: false });
          return m;
        });
      }
    });
  };

  // Re-fetch mood results when moods change via URL (e.g. back button)
  useEffect(() => {
    for (const label of selectedMoods) {
      if (!moodMovies.has(label)) {
        const preset = MOOD_PRESETS.find((p) => p.label === label);
        const query = preset ? preset.query : label;
        fetchMoodResults(query, label);
      }
    }
    // Clean up moods that were removed from URL
    for (const label of moodMovies.keys()) {
      if (!selectedMoods.has(label)) {
        moodAbortControllers.current.get(label)?.abort();
        moodAbortControllers.current.delete(label);
        setMoodMovies((prev) => {
          const m = new Map(prev);
          m.delete(label);
          return m;
        });
      }
    }
  }, [selectedMoodsParam]);

  // --- Filter text debounce ---
  useEffect(() => {
    if (filterDebounceRef.current) clearTimeout(filterDebounceRef.current);
    filterDebounceRef.current = setTimeout(() => {
      updateParams({
        director: directorInput || null,
        keyword: keywordInput || null,
        cast: castInput || null,
        min_rating: minRatingInput || null,
        max_rating: maxRatingInput || null,
        min_runtime: minRuntimeInput || null,
        max_runtime: maxRuntimeInput || null,
        offset: null,
      });
    }, 600);
    return () => {
      if (filterDebounceRef.current) clearTimeout(filterDebounceRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [directorInput, keywordInput, castInput, minRatingInput, maxRatingInput, minRuntimeInput, maxRuntimeInput]);

  // --- Load genres & languages once ---
  useEffect(() => {
    getGenres().then((data) => setGenres(data.genres)).catch(() => {});
    getLanguages().then((data) => setLanguages(data.languages)).catch(() => {});
  }, []);

  // --- Refresh movie metadata helper ---
  const refreshMovieMeta = (ids: number[]) => {
    refreshForMovieIds(ids);
    refreshDismissedForMovieIds(ids);
    refreshRatingsForMovieIds(ids);
    fetchMatchPercents(ids);
  };

  // --- Main data fetch (title search / advanced / combined) ---
  useEffect(() => {
    if (searchMode === "idle" || searchMode === "mood") return;

    setLoading(true);
    setError("");

    if (searchMode === "title") {
      // Pure title search
      searchMovies(q, 40)
        .then((data) => {
          setResults(data.results.map((m) => ({ movie: m })));
          setTotal(data.total);
          refreshMovieMeta(data.results.map((m) => m.id));
        })
        .catch((e) => setError(e.detail || e.message))
        .finally(() => setLoading(false));
    } else {
      // Advanced or combined: use advanced search API
      const parsedMin = debouncedMinRating ? Number(debouncedMinRating) : undefined;
      const parsedMax = debouncedMaxRating ? Number(debouncedMaxRating) : undefined;
      const parsedMinRuntime = debouncedMinRuntime ? Number(debouncedMinRuntime) : undefined;
      const parsedMaxRuntime = debouncedMaxRuntime ? Number(debouncedMaxRuntime) : undefined;

      advancedSearchMovies({
        genre: selectedGenre ?? undefined,
        decade: selectedDecade ?? undefined,
        min_rating: parsedMin != null && parsedMin >= 0 ? parsedMin : undefined,
        max_rating: parsedMax != null && parsedMax >= 0 ? parsedMax : undefined,
        director: debouncedDirector || undefined,
        keyword: debouncedKeyword || (q || undefined),
        cast: debouncedCast || undefined,
        language: selectedLanguage ?? undefined,
        min_runtime: parsedMinRuntime && parsedMinRuntime >= 1 ? parsedMinRuntime : undefined,
        max_runtime: parsedMaxRuntime && parsedMaxRuntime >= 1 ? parsedMaxRuntime : undefined,
        sort_by: sortBy,
        offset,
        limit: PAGE_SIZE,
      })
        .then((data) => {
          setResults(data.results.map((r) => ({ movie: r.movie })));
          setTotal(data.total);
          refreshMovieMeta(data.results.map((r) => r.movie.id));
        })
        .catch((e) => setError(e.detail || e.message))
        .finally(() => setLoading(false));
    }
  }, [q, selectedGenre, selectedDecade, selectedLanguage, sortBy, debouncedDirector, debouncedKeyword, debouncedCast, debouncedMinRating, debouncedMaxRating, debouncedMinRuntime, debouncedMaxRuntime, offset, searchMode]);

  // --- Merge mood results into a flat list when in mood-only mode ---
  const moodOnlyResults: UnifiedMovie[] = searchMode === "mood"
    ? [...moodMovies.values()].flatMap((v) => v.movies.map((m) => ({ movie: m, isPersonalized: v.isPersonalized })))
    : [];
  const moodLoading = searchMode === "mood" && [...moodMovies.values()].some((v) => v.loading);

  // Final display results
  const displayResults = searchMode === "mood" ? moodOnlyResults : results;
  const displayTotal = searchMode === "mood" ? moodOnlyResults.length : total;
  const displayLoading = searchMode === "mood" ? moodLoading : loading;

  // --- Pagination (for non-mood modes) ---
  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
  const showPagination = searchMode !== "mood" && searchMode !== "idle" && totalPages > 1;

  // --- Active filters for chips ---
  const activeFilters: { key: string; label: string }[] = [];
  if (selectedGenre) activeFilters.push({ key: "genre", label: `Genre: ${selectedGenre}` });
  if (selectedDecade) activeFilters.push({ key: "decade", label: `Decade: ${selectedDecade}` });
  if (debouncedMinRating) activeFilters.push({ key: "min_rating", label: `Min Rating: ${debouncedMinRating}` });
  if (debouncedMaxRating) activeFilters.push({ key: "max_rating", label: `Max Rating: ${debouncedMaxRating}` });
  if (debouncedDirector) activeFilters.push({ key: "director", label: `Director: ${debouncedDirector}` });
  if (debouncedKeyword) activeFilters.push({ key: "keyword", label: `Keyword: ${debouncedKeyword}` });
  if (debouncedCast) activeFilters.push({ key: "cast", label: `Cast: ${debouncedCast}` });
  if (selectedLanguage) activeFilters.push({ key: "language", label: `Language: ${languageName(selectedLanguage)}` });
  if (debouncedMinRuntime) activeFilters.push({ key: "min_runtime", label: `Min Runtime: ${debouncedMinRuntime}min` });
  if (debouncedMaxRuntime) activeFilters.push({ key: "max_runtime", label: `Max Runtime: ${debouncedMaxRuntime}min` });

  const clearAllFilters = () => {
    setDirectorInput("");
    setKeywordInput("");
    setCastInput("");
    setMinRatingInput("");
    setMaxRatingInput("");
    setMinRuntimeInput("");
    setMaxRuntimeInput("");
    setParams((prev) => {
      const next = new URLSearchParams();
      // Preserve non-filter params
      const keep = prev.get("q");
      const moods = prev.get("moods");
      if (keep) next.set("q", keep);
      if (moods) next.set("moods", moods);
      return next;
    });
  };

  const removeFilter = (key: string) => {
    if (key === "director") setDirectorInput("");
    if (key === "keyword") setKeywordInput("");
    if (key === "cast") setCastInput("");
    if (key === "min_rating") setMinRatingInput("");
    if (key === "max_rating") setMaxRatingInput("");
    if (key === "min_runtime") setMinRuntimeInput("");
    if (key === "max_runtime") setMaxRuntimeInput("");
    updateParams({ [key]: null, offset: null });
  };

  // Deduplicate mood results by movie id
  const seen = new Set<number>();
  const deduped = displayResults.filter((r) => {
    if (seen.has(r.movie.id)) return false;
    seen.add(r.movie.id);
    return true;
  });

  return (
    <>
      {/* Header */}
      <header className="mb-8">
        <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
          Search
        </h1>
        <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
          CineMatch-AI Intelligence Engine
        </p>
      </header>

      {/* Search bar */}
      <div className="mb-6">
        <div className="relative max-w-2xl">
          <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-outline/60 text-xl">search</span>
          <input
            type="text"
            value={searchInput}
            onChange={(e) => handleSearchInput(e.target.value)}
            placeholder="Search by title, vibe, or description..."
            className="w-full h-12 pl-12 pr-5 bg-surface-container-lowest border border-outline-variant/20 rounded-full text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint focus:outline-none font-body text-base"
          />
          {searchInput && (
            <button
              onClick={() => handleSearchInput("")}
              className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-on-surface transition-colors"
            >
              <span className="material-symbols-outlined text-xl">close</span>
            </button>
          )}
        </div>
      </div>

      {/* Mood chips — always visible */}
      <div className="flex flex-wrap gap-3 mb-6">
        {MOOD_PRESETS.map((mood) => {
          const isActive = selectedMoods.has(mood.label);
          const moodData = moodMovies.get(mood.label);
          const isLoading = moodData?.loading ?? false;
          return (
            <button
              key={mood.label}
              onClick={() => toggleMood(mood)}
              disabled={isLoading && !isActive}
              className={`flex items-center gap-2 px-5 py-2.5 rounded-full font-label text-sm font-bold tracking-wide transition-all duration-300 border ${
                isActive
                  ? "bg-primary text-on-primary border-primary shadow-[0_0_20px_rgba(255,193,7,0.3)]"
                  : "bg-surface-container-low text-on-surface-variant border-outline-variant/20 hover:bg-surface-container hover:border-outline-variant/40"
              } ${isLoading && !isActive ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
            >
              <span className="material-symbols-outlined text-[18px]">{mood.icon}</span>
              {mood.label}
            </button>
          );
        })}
      </div>

      {/* Filters toggle */}
      <div className="mb-6">
        <button
          onClick={() => setFiltersOpen((v) => !v)}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high transition-colors font-label text-sm font-bold uppercase tracking-widest"
        >
          <span className="material-symbols-outlined text-lg">tune</span>
          Filters
          {activeFilterCount > 0 && (
            <span className="ml-1 inline-flex items-center justify-center w-5 h-5 rounded-full bg-primary text-on-primary text-xs font-bold">
              {activeFilterCount}
            </span>
          )}
          <span className="material-symbols-outlined text-lg ml-1">
            {filtersOpen ? "expand_less" : "expand_more"}
          </span>
        </button>
      </div>

      {/* Collapsible advanced filters */}
      {filtersOpen && (
        <div className="glass-panel p-6 rounded-2xl border border-outline-variant/10 mb-6 space-y-6">
          {/* Genre chips */}
          <div>
            <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 block">Genre</span>
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
            <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 block">Decade</span>
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

          {/* Rating range + Sort + Language + Runtime */}
          <div className="flex flex-wrap gap-4 items-end">
            <div className="space-y-2">
              <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">Min Rating</label>
              <input type="number" min="0" max="10" step="0.5" placeholder="e.g. 7" value={minRatingInput} onChange={(e) => setMinRatingInput(e.target.value)}
                className="w-24 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm" />
            </div>
            <div className="space-y-2">
              <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">Max Rating</label>
              <input type="number" min="0" max="10" step="0.5" placeholder="e.g. 9" value={maxRatingInput} onChange={(e) => setMaxRatingInput(e.target.value)}
                className="w-24 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm" />
            </div>
            <div className="space-y-2">
              <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">Sort by</label>
              <div className="relative">
                <select value={sortBy} onChange={(e) => updateParams({ sort_by: e.target.value, offset: null })}
                  className="bg-surface-container-lowest border-none rounded-lg p-3 pr-10 text-on-surface appearance-none focus:ring-2 focus:ring-surface-tint font-body text-sm">
                  {SORT_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
                <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none">
                  <span className="material-symbols-outlined text-outline text-sm">expand_more</span>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">Language</label>
              <div className="relative">
                <select value={selectedLanguage || ""} onChange={(e) => updateParams({ language: e.target.value || null, offset: null })}
                  className="bg-surface-container-lowest border-none rounded-lg p-3 pr-10 text-on-surface appearance-none focus:ring-2 focus:ring-surface-tint font-body text-sm">
                  <option value="">All Languages</option>
                  {languages.map((l) => (
                    <option key={l.code} value={l.code}>{languageName(l.code)} ({l.count.toLocaleString()})</option>
                  ))}
                </select>
                <div className="absolute inset-y-0 right-3 flex items-center pointer-events-none">
                  <span className="material-symbols-outlined text-outline text-sm">expand_more</span>
                </div>
              </div>
            </div>
            <div className="space-y-2">
              <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">Min Runtime</label>
              <input type="number" min="1" placeholder="e.g. 90" value={minRuntimeInput} onChange={(e) => setMinRuntimeInput(e.target.value)}
                className="w-28 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm" />
            </div>
            <div className="space-y-2">
              <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">Max Runtime</label>
              <input type="number" min="1" placeholder="e.g. 150" value={maxRuntimeInput} onChange={(e) => setMaxRuntimeInput(e.target.value)}
                className="w-28 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm" />
            </div>
            {activeFilters.length > 0 && (
              <button onClick={clearAllFilters}
                className="px-4 py-3 rounded-lg text-xs font-bold uppercase tracking-widest text-error hover:bg-error/10 transition-colors">
                Clear All
              </button>
            )}
          </div>

          {/* Text filter inputs */}
          <div className="flex flex-wrap gap-4">
            <div className="space-y-2 flex-1 min-w-[200px]">
              <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">Director</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                  <span className="material-symbols-outlined text-outline text-lg">movie_filter</span>
                </div>
                <input type="text" placeholder="e.g. Nolan" value={directorInput} onChange={(e) => setDirectorInput(e.target.value)}
                  className="w-full pl-10 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm" />
              </div>
            </div>
            <div className="space-y-2 flex-1 min-w-[200px]">
              <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">Keyword</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                  <span className="material-symbols-outlined text-outline text-lg">sell</span>
                </div>
                <input type="text" placeholder="e.g. dystopia" value={keywordInput} onChange={(e) => setKeywordInput(e.target.value)}
                  className="w-full pl-10 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm" />
              </div>
            </div>
            <div className="space-y-2 flex-1 min-w-[200px]">
              <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">Cast</label>
              <div className="relative">
                <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                  <span className="material-symbols-outlined text-outline text-lg">theater_comedy</span>
                </div>
                <input type="text" placeholder="e.g. DiCaprio" value={castInput} onChange={(e) => setCastInput(e.target.value)}
                  className="w-full pl-10 bg-surface-container-lowest border-none rounded-lg p-3 text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint font-body text-sm" />
              </div>
            </div>
          </div>
        </div>
      )}

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

      {/* Result count */}
      {searchMode !== "idle" && !displayLoading && !error && (
        <p className="mb-6 text-on-surface-variant text-sm">
          {searchMode === "mood" ? (
            <>Found <span className="text-primary-container font-bold">{deduped.length}</span> movies for selected moods</>
          ) : (
            <>
              <span className="text-primary-container font-bold">{displayTotal.toLocaleString()}</span> movie{displayTotal !== 1 ? "s" : ""} found
              {q && <> for <span className="italic text-primary">"{q}"</span></>}
            </>
          )}
        </p>
      )}

      {/* Loading / Error */}
      {displayLoading && <LoadingSpinner text="Searching..." />}
      {error && <ErrorPanel message={error} onRetry={() => updateParams({ offset: null })} />}

      {/* Results grid */}
      {!displayLoading && !error && (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {deduped.map((r) => (
            <MovieCard
              key={r.movie.id}
              movie={r.movie}
              isBookmarked={isInWatchlist(r.movie.id)}
              onToggleBookmark={toggle}
              onAddToList={(id) => setAddToListMovieId(id)}
              isDismissed={isDismissed(r.movie.id)}
              onDismiss={toggleDismiss}
              userRating={getRating(r.movie.id)}
              matchPercent={getMatchPercent(r.movie.id)}
            />
          ))}
        </section>
      )}

      {/* Empty state */}
      {!displayLoading && !error && deduped.length === 0 && searchMode === "idle" && (
        <div className="text-center py-20">
          <span className="material-symbols-outlined text-6xl text-outline/30 mb-4 block">movie_filter</span>
          <p className="text-on-surface-variant text-lg">
            Search by title, select a mood, or use filters to discover movies
          </p>
        </div>
      )}

      {!displayLoading && !error && deduped.length === 0 && searchMode !== "idle" && (
        <p className="text-center text-on-surface-variant text-lg py-20">
          No movies found. Try a different search or adjust your filters.
        </p>
      )}

      {/* Pagination */}
      {showPagination && !loading && !error && (
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

      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
    </>
  );
}
