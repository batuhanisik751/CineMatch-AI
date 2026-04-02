import { useEffect, useRef, useState } from "react";
import { getMoviesByCast, searchActors } from "../../api/movies";
import type { ActorSummary, AdvancedSearchResult } from "../../api/types";
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

export default function CastComboTab() {
  useUserId();
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } =
    useDismissed();
  const { getMatchPercent, fetchMatchPercents } = useMatchPredictions();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  // Actor search state
  const [searchQuery, setSearchQuery] = useState("");
  const [suggestions, setSuggestions] = useState<ActorSummary[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedActors, setSelectedActors] = useState<string[]>([]);

  // Results state
  const [results, setResults] = useState<AdvancedSearchResult[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [sortBy, setSortBy] = useState("popularity");
  const [sortOrder, setSortOrder] = useState("desc");

  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [error, setError] = useState("");

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Debounced actor search
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
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(e.target as Node)
      ) {
        setShowDropdown(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  // Fetch results when actors, sort, or offset change
  useEffect(() => {
    if (selectedActors.length < 2) {
      setResults([]);
      setTotal(0);
      return;
    }

    setLoading(true);
    setError("");
    getMoviesByCast(selectedActors, sortBy, sortOrder, offset, PAGE_SIZE)
      .then((data) => {
        setResults(data.results);
        setTotal(data.total);
        const ids = data.results.map((r) => r.movie.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        fetchMatchPercents(ids);
      })
      .catch((e) => setError(e.detail || e.message || "Search failed"))
      .finally(() => setLoading(false));
  }, [selectedActors, sortBy, sortOrder, offset]);

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

  const totalPages = Math.ceil(total / PAGE_SIZE);
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1;

  return (
    <>
      <header className="mb-10">
        <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
          Cast Combo
        </h1>
        <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
          Find movies where your favorite actors appear together
        </p>
      </header>

      {/* Actor search + chips */}
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
              placeholder={
                selectedActors.length === 0
                  ? "Search for an actor to add..."
                  : "Add another actor..."
              }
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
                        {a.film_count} film{a.film_count !== 1 ? "s" : ""}
                        {" \u00B7 "}
                        {a.avg_vote.toFixed(1)} avg
                      </span>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}

        {selectedActors.length < 2 && selectedActors.length > 0 && (
          <p className="text-on-surface-variant text-xs mt-2">
            Add at least one more actor to search
          </p>
        )}
      </div>

      {/* Sort controls */}
      {selectedActors.length >= 2 && (
        <div className="flex flex-wrap items-center gap-4 mb-6">
          <p className="text-on-surface-variant text-sm">
            {total} movie{total !== 1 ? "s" : ""} found
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
      {loading && <LoadingSpinner text="Searching cast combinations..." />}
      {error && (
        <ErrorPanel
          message={error}
          onRetry={() => setOffset((o) => o)}
        />
      )}

      {/* Results grid */}
      {!loading && !error && results.length > 0 && (
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
          {results.map((item) => (
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
      )}

      {/* Empty state */}
      {!loading &&
        !error &&
        results.length === 0 &&
        selectedActors.length >= 2 && (
          <p className="text-center text-on-surface-variant text-lg py-20">
            No movies found featuring all selected actors together. Try
            removing an actor.
          </p>
        )}

      {/* Prompt state */}
      {selectedActors.length === 0 && !loading && (
        <div className="text-center py-20">
          <span className="material-symbols-outlined text-6xl text-on-surface-variant/30 mb-4 block">
            group
          </span>
          <p className="text-on-surface-variant text-lg">
            Search and select at least 2 actors to find movies they appear
            in together
          </p>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && !loading && (
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
      <AddToListModal
        movieId={addToListMovieId}
        onClose={() => setAddToListMovieId(null)}
      />
    </>
  );
}
