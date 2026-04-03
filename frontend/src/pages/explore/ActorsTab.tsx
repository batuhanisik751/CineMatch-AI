import { useEffect, useRef, useState } from "react";
import {
  getActorFilmography,
  getMoviesByCast,
  getPopularActors,
  searchActors,
} from "../../api/movies";
import type {
  ActorFilmResult,
  ActorStats,
  ActorSummary,
  AdvancedSearchResult,
} from "../../api/types";
import ErrorPanel from "../../components/ErrorPanel";
import LoadingSpinner from "../../components/LoadingSpinner";
import MovieCard from "../../components/MovieCard";
import AddToListModal from "../../components/AddToListModal";
import { useUserId } from "../../hooks/useUserId";
import { useDismissed } from "../../hooks/useDismissed";
import { useMatchPredictions } from "../../hooks/useMatchPredictions";
import { useWatchlist } from "../../hooks/useWatchlist";

const SORT_OPTIONS = [
  { value: "popularity", label: "Popularity" },
  { value: "vote_average", label: "Rating" },
  { value: "release_date", label: "Release Date" },
  { value: "title", label: "Title" },
];

const PAGE_SIZE = 20;

export default function ActorsTab() {
  const { userId } = useUserId();
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getMatchPercent, fetchMatchPercents } = useMatchPredictions();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  // Chip-based actor selection
  const [selectedActors, setSelectedActors] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [suggestions, setSuggestions] = useState<ActorSummary[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);

  // Browse mode state (0 actors selected)
  const [popularActors, setPopularActors] = useState<ActorSummary[]>([]);

  // Filmography mode state (1 actor selected)
  const [filmography, setFilmography] = useState<ActorFilmResult[]>([]);
  const [stats, setStats] = useState<ActorStats | null>(null);

  // Cast combo mode state (2+ actors selected)
  const [comboResults, setComboResults] = useState<AdvancedSearchResult[]>([]);
  const [comboTotal, setComboTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [sortBy, setSortBy] = useState("popularity");
  const [sortOrder, setSortOrder] = useState("desc");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const mode = selectedActors.length === 0 ? "browse" : selectedActors.length === 1 ? "filmography" : "combo";

  // Load popular actors on mount
  useEffect(() => {
    setLoading(true);
    getPopularActors(30)
      .then((data) => setPopularActors(data.results))
      .catch((e) => setError(e.detail || e.message || "Failed to load actors"))
      .finally(() => setLoading(false));
  }, []);

  // Debounced typeahead search for dropdown suggestions
  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);

    if (!searchQuery.trim()) {
      setSuggestions([]);
      setShowDropdown(false);
      return;
    }

    debounceRef.current = setTimeout(() => {
      setSearchLoading(true);
      searchActors(searchQuery.trim(), 10)
        .then((data) => {
          setSuggestions(
            data.results.filter((a) => !selectedActors.includes(a.name))
          );
          setShowDropdown(true);
        })
        .catch(() => setSuggestions([]))
        .finally(() => setSearchLoading(false));
    }, 300);

    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchQuery, selectedActors]);

  // Close dropdown on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Mode transitions: fetch data when selectedActors changes
  useEffect(() => {
    if (selectedActors.length === 0) {
      // Browse mode — popular actors already loaded
      setFilmography([]);
      setStats(null);
      setComboResults([]);
      setComboTotal(0);
      return;
    }

    if (selectedActors.length === 1) {
      // Filmography mode
      setComboResults([]);
      setComboTotal(0);
      setLoading(true);
      setError("");
      getActorFilmography(selectedActors[0], userId)
        .then((data) => {
          setFilmography(data.filmography);
          setStats(data.stats);
          const ids = data.filmography.map((f) => f.movie.id);
          refreshForMovieIds(ids);
          refreshDismissedForMovieIds(ids);
          fetchMatchPercents(ids);
        })
        .catch((e) => setError(e.detail || e.message || "Failed to load filmography"))
        .finally(() => setLoading(false));
      return;
    }

    // Cast combo mode (2+)
    setFilmography([]);
    setStats(null);
    setLoading(true);
    setError("");
    getMoviesByCast(selectedActors, sortBy, sortOrder, offset, PAGE_SIZE)
      .then((data) => {
        setComboResults(data.results);
        setComboTotal(data.total);
        const ids = data.results.map((r) => r.movie.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        fetchMatchPercents(ids);
      })
      .catch((e) => setError(e.detail || e.message || "Search failed"))
      .finally(() => setLoading(false));
  }, [selectedActors, sortBy, sortOrder, offset]);

  // Filter popular actors by search query in browse mode
  const filteredPopularActors =
    mode === "browse" && searchQuery.trim()
      ? popularActors.filter((a) =>
          a.name.toLowerCase().includes(searchQuery.trim().toLowerCase())
        )
      : popularActors;

  const addActor = (name: string) => {
    if (selectedActors.length >= 5) return;
    setSelectedActors((prev) => [...prev, name]);
    setSearchQuery("");
    setSuggestions([]);
    setShowDropdown(false);
    setOffset(0);
  };

  const removeActor = (name: string) => {
    setSelectedActors((prev) => prev.filter((a) => a !== name));
    setOffset(0);
  };

  const totalPages = Math.ceil(comboTotal / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  const searchPlaceholder =
    selectedActors.length === 0
      ? "Search actors..."
      : selectedActors.length === 1
        ? "Add another actor to find shared movies..."
        : selectedActors.length >= 5
          ? ""
          : "Add another actor...";

  return (
    <>
      <header className="mb-10">
        <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
          {mode === "filmography" ? selectedActors[0] : "Actors"}
        </h1>
        <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
          {mode === "browse" && "Browse filmographies or find movies actors share"}
          {mode === "filmography" && "Actor filmography"}
          {mode === "combo" && "Movies featuring all selected actors"}
        </p>

        {/* Stats bar for filmography mode */}
        {mode === "filmography" && stats && (
          <div className="flex flex-wrap items-center gap-4 mt-4">
            <span className="glass-card rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-widest text-on-surface-variant">
              {stats.total_films} film{stats.total_films !== 1 ? "s" : ""}
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

      {/* Chip-based search */}
      <div className="mb-10 max-w-2xl">
        {/* Selected actor chips */}
        {selectedActors.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {selectedActors.map((name) => (
              <span
                key={name}
                className="inline-flex items-center gap-1.5 bg-[#FFC107]/15 text-[#FFC107] rounded-full px-3 py-1.5 text-sm font-bold"
              >
                <span className="material-symbols-outlined text-base">
                  person
                </span>
                {name}
                <button
                  onClick={() => removeActor(name)}
                  className="ml-1 hover:text-white transition-colors"
                >
                  <span className="material-symbols-outlined text-base">
                    close
                  </span>
                </button>
              </span>
            ))}
          </div>
        )}

        {/* Search input with dropdown */}
        {selectedActors.length < 5 && (
          <div className="relative" ref={dropdownRef}>
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-xl">
              search
            </span>
            <input
              type="text"
              placeholder={searchPlaceholder}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onFocus={() => {
                if (suggestions.length > 0) setShowDropdown(true);
              }}
              className="w-full pl-10 pr-4 py-3 rounded-xl bg-surface-container-highest text-on-surface placeholder:text-on-surface-variant text-sm font-medium border border-white/5 focus:outline-none focus:border-[#FFC107]/50 transition-colors"
            />
            {searchLoading && (
              <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-xl animate-spin">
                progress_activity
              </span>
            )}

            {/* Dropdown */}
            {showDropdown && suggestions.length > 0 && (
              <div className="absolute z-50 w-full mt-1 rounded-xl bg-surface-container-highest border border-white/10 shadow-xl overflow-hidden">
                {suggestions.map((a) => (
                  <button
                    key={a.name}
                    onClick={() => addActor(a.name)}
                    className="w-full px-4 py-3 text-left hover:bg-surface-container-high transition-colors flex items-center gap-3"
                  >
                    <div className="w-8 h-8 rounded-full bg-[#FFC107]/10 flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-[#FFC107] text-lg">
                        theater_comedy
                      </span>
                    </div>
                    <div>
                      <span className="text-on-surface text-sm font-medium">
                        {a.name}
                      </span>
                      <span className="text-on-surface-variant text-xs ml-2">
                        {a.film_count} film{a.film_count !== 1 ? "s" : ""}{" · "}
                        {a.avg_vote.toFixed(1)} avg
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Sort controls for combo mode */}
      {mode === "combo" && (
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <p className="text-on-surface-variant text-sm">
            {comboTotal} movie{comboTotal !== 1 ? "s" : ""} found
          </p>
          <select
            value={sortBy}
            onChange={(e) => {
              setSortBy(e.target.value);
              setOffset(0);
            }}
            className="bg-surface-container-highest text-on-surface text-sm rounded-lg px-3 py-2 border border-white/5 focus:outline-none focus:border-[#FFC107]/50"
          >
            {SORT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
          <button
            onClick={() => {
              setSortOrder((prev) => (prev === "desc" ? "asc" : "desc"));
              setOffset(0);
            }}
            className="flex items-center gap-1 text-on-surface-variant hover:text-on-surface text-sm transition-colors"
          >
            <span className="material-symbols-outlined text-lg">
              {sortOrder === "desc" ? "arrow_downward" : "arrow_upward"}
            </span>
            {sortOrder === "desc" ? "Desc" : "Asc"}
          </button>
        </div>
      )}

      {/* Loading & error */}
      {loading && (
        <LoadingSpinner
          text={
            mode === "browse"
              ? "Loading actors..."
              : mode === "filmography"
                ? `Loading ${selectedActors[0]}'s filmography...`
                : "Searching cast combinations..."
          }
        />
      )}
      {error && (
        <ErrorPanel
          message={error}
          onRetry={() => {
            if (mode === "filmography") {
              setSelectedActors([...selectedActors]);
            } else {
              window.location.reload();
            }
          }}
        />
      )}

      {/* Browse mode: popular actors grid */}
      {mode === "browse" && !loading && !error && (
        <>
          {filteredPopularActors.length > 0 ? (
            <>
              <p className="text-on-surface-variant text-sm mb-6">
                {searchQuery.trim()
                  ? `${filteredPopularActors.length} result${filteredPopularActors.length !== 1 ? "s" : ""} for "${searchQuery}"`
                  : "Popular actors"}
              </p>
              <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                {filteredPopularActors.map((a) => (
                  <button
                    key={a.name}
                    onClick={() => addActor(a.name)}
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
                          style={{ fontVariationSettings: "'FILL' 1" }}
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
          ) : (
            <p className="text-center text-on-surface-variant text-lg py-20">
              No actors found
              {searchQuery.trim() ? ` for "${searchQuery}"` : ""}. Try a
              different search.
            </p>
          )}
        </>
      )}

      {/* Filmography mode: actor's movies */}
      {mode === "filmography" && !loading && !error && (
        <>
          {filmography.length > 0 ? (
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
                      onToggleBookmark={toggle}
                      onAddToList={(id) => setAddToListMovieId(id)}
                      isDismissed={isDismissed(item.movie.id)}
                      onDismiss={toggleDismiss}
                      matchPercent={getMatchPercent(item.movie.id)}
                    />
                    <div className="mt-2 flex items-center gap-3 text-xs font-medium">
                      {item.user_rating != null ? (
                        <span className="text-[#FFC107]">
                          <span
                            className="material-symbols-outlined text-sm align-middle mr-1"
                            style={{ fontVariationSettings: "'FILL' 1" }}
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
          ) : (
            <p className="text-center text-on-surface-variant text-lg py-20">
              No movies found for {selectedActors[0]}.
            </p>
          )}
        </>
      )}

      {/* Combo mode: shared movies */}
      {mode === "combo" && !loading && !error && (
        <>
          {comboResults.length > 0 ? (
            <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
              {comboResults.map((item) => (
                <MovieCard
                  key={item.movie.id}
                  movie={item.movie}
                  isBookmarked={isInWatchlist(item.movie.id)}
                  onToggleBookmark={toggle}
                  onAddToList={(id) => setAddToListMovieId(id)}
                  isDismissed={isDismissed(item.movie.id)}
                  onDismiss={toggleDismiss}
                  matchPercent={getMatchPercent(item.movie.id)}
                />
              ))}
            </section>
          ) : (
            <p className="text-center text-on-surface-variant text-lg py-20">
              No movies found featuring all selected actors together. Try
              removing an actor.
            </p>
          )}
        </>
      )}

      {/* Pagination for combo mode */}
      {mode === "combo" && totalPages > 1 && !loading && (
        <div className="flex items-center justify-center gap-4 mt-10">
          <button
            onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
            disabled={offset === 0}
            className="px-4 py-2 rounded-lg bg-surface-container-highest text-on-surface text-sm font-medium disabled:opacity-30 hover:bg-surface-container-high transition-colors"
          >
            Previous
          </button>
          <span className="text-on-surface-variant text-sm">
            Page {currentPage} of {totalPages}
          </span>
          <button
            onClick={() => setOffset((o) => o + PAGE_SIZE)}
            disabled={currentPage >= totalPages}
            className="px-4 py-2 rounded-lg bg-surface-container-highest text-on-surface text-sm font-medium disabled:opacity-30 hover:bg-surface-container-high transition-colors"
          >
            Next
          </button>
        </div>
      )}

      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
    </>
  );
}
