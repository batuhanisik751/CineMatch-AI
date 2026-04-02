import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { autocompleteMovies, compareMovies } from "../api/movies";
import type {
  AutocompleteSuggestion,
  MovieComparisonResponse,
  MovieResponse,
} from "../api/types";
import TopNav from "../components/TopNav";
import BottomNav from "../components/BottomNav";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorPanel from "../components/ErrorPanel";
import { useUserId } from "../hooks/useUserId";

function posterUrl(path: string | null, size = "w300") {
  return path ? `https://image.tmdb.org/t/p/${size}${path}` : null;
}

/* ---------- Movie selector with autocomplete ---------- */
function MovieSelector({
  label,
  selected,
  onSelect,
  onClear,
  excludeId,
}: {
  label: string;
  selected: AutocompleteSuggestion | null;
  onSelect: (s: AutocompleteSuggestion) => void;
  onClear: () => void;
  excludeId?: number;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AutocompleteSuggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node))
        setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSearch = useCallback(
    (q: string) => {
      setQuery(q);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (q.trim().length < 2) {
        setResults([]);
        setOpen(false);
        return;
      }
      setSearching(true);
      debounceRef.current = setTimeout(() => {
        autocompleteMovies(q.trim(), 8)
          .then((res) => {
            setResults(
              res.results.filter((m) => excludeId == null || m.id !== excludeId),
            );
            setOpen(true);
          })
          .catch(() => setResults([]))
          .finally(() => setSearching(false));
      }, 300);
    },
    [excludeId],
  );

  if (selected) {
    const poster = posterUrl(selected.poster_path, "w92");
    return (
      <div className="glass-card rounded-2xl p-4 flex items-center gap-4">
        {poster ? (
          <img src={poster} alt="" className="w-12 h-18 rounded-lg object-cover" />
        ) : (
          <div className="w-12 h-18 rounded-lg bg-surface-container flex items-center justify-center">
            <span className="material-symbols-outlined text-on-surface-variant">movie</span>
          </div>
        )}
        <div className="flex-1 min-w-0">
          <p className="text-on-surface font-bold truncate">{selected.title}</p>
          {selected.year && (
            <p className="text-sm text-on-surface-variant">{selected.year}</p>
          )}
        </div>
        <button
          onClick={onClear}
          className="p-2 rounded-lg hover:bg-surface-container transition-colors"
        >
          <span className="material-symbols-outlined text-on-surface-variant">close</span>
        </button>
      </div>
    );
  }

  return (
    <div ref={wrapperRef} className="relative">
      <label className="text-xs uppercase tracking-widest text-on-surface-variant font-label mb-2 block">
        {label}
      </label>
      <div className="relative">
        <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">
          search
        </span>
        <input
          type="text"
          value={query}
          onChange={(e) => handleSearch(e.target.value)}
          placeholder="Search for a movie..."
          className="w-full pl-10 pr-4 py-3 rounded-xl bg-surface-container border border-outline-variant/20 text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:border-primary/50 transition-colors"
        />
        {searching && (
          <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant animate-spin">
            progress_activity
          </span>
        )}
      </div>
      {open && results.length > 0 && (
        <div className="absolute z-50 mt-2 w-full bg-surface-container-high rounded-xl border border-outline-variant/20 shadow-2xl max-h-72 overflow-y-auto">
          {results.map((r) => {
            const p = posterUrl(r.poster_path, "w92");
            return (
              <button
                key={r.id}
                onClick={() => {
                  onSelect(r);
                  setQuery("");
                  setOpen(false);
                }}
                className="w-full flex items-center gap-3 px-4 py-3 hover:bg-surface-container transition-colors text-left"
              >
                {p ? (
                  <img src={p} alt="" className="w-8 h-12 rounded object-cover" />
                ) : (
                  <div className="w-8 h-12 rounded bg-surface-container flex items-center justify-center">
                    <span className="material-symbols-outlined text-xs text-on-surface-variant">movie</span>
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-on-surface font-medium truncate">{r.title}</p>
                  {r.year && <p className="text-xs text-on-surface-variant">{r.year}</p>}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ---------- Pill with optional highlight ---------- */
function Pill({
  text,
  highlighted,
  icon,
}: {
  text: string;
  highlighted?: boolean;
  icon?: string;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-semibold border transition-colors ${
        highlighted
          ? "bg-primary/20 text-primary border-primary/40"
          : "bg-surface-container-low text-on-surface-variant border-outline-variant/20"
      }`}
    >
      {icon && (
        <span className="material-symbols-outlined" style={{ fontSize: "14px" }}>
          {icon}
        </span>
      )}
      {text}
    </span>
  );
}

/* ---------- Movie detail column ---------- */
function MovieColumn({
  movie,
  rc,
  side,
  sharedGenres,
  sharedActors,
  sharedKeywords,
  alsScore,
}: {
  movie: MovieResponse;
  rc: { avg: number; count: number };
  side: "left" | "right";
  sharedGenres: Set<string>;
  sharedActors: Set<string>;
  sharedKeywords: Set<string>;
  alsScore?: number | null;
}) {
  const poster = posterUrl(movie.poster_path, "w300");
  const year = movie.release_date?.slice(0, 4);
  return (
    <div className="glass-panel rounded-2xl p-6 space-y-5">
      {/* Poster */}
      <div className="flex justify-center">
        {poster ? (
          <img
            src={poster}
            alt={movie.title}
            className={`w-48 rounded-xl shadow-2xl ${side === "left" ? "rotate-[-1deg]" : "rotate-[1deg]"}`}
          />
        ) : (
          <div className="w-48 h-72 rounded-xl bg-surface-container flex items-center justify-center">
            <span className="material-symbols-outlined text-5xl text-on-surface-variant">movie</span>
          </div>
        )}
      </div>

      {/* Title + meta */}
      <div className="text-center space-y-1">
        <h2 className="text-2xl font-headline font-bold text-on-surface">{movie.title}</h2>
        <p className="text-sm text-on-surface-variant">
          {[year, movie.runtime ? `${movie.runtime} min` : null, movie.original_language?.toUpperCase()]
            .filter(Boolean)
            .join(" \u00b7 ")}
        </p>
        {movie.director && (
          <p className="text-sm text-on-surface-variant">
            Directed by <span className="text-on-surface font-medium">{movie.director}</span>
          </p>
        )}
      </div>

      {/* Community rating */}
      <div className="flex items-center justify-center gap-4">
        <div className="text-center">
          <div className="flex items-center gap-1 justify-center">
            <span className="material-symbols-outlined text-primary-fixed-dim" style={{ fontVariationSettings: "'FILL' 1", fontSize: "18px" }}>star</span>
            <span className="text-on-surface font-bold text-lg">{movie.vote_average.toFixed(1)}</span>
          </div>
          <p className="text-xs text-on-surface-variant">TMDb</p>
        </div>
        <div className="w-px h-8 bg-outline-variant/20" />
        <div className="text-center">
          <p className="text-on-surface font-bold text-lg">{rc.avg > 0 ? rc.avg.toFixed(1) : "N/A"}</p>
          <p className="text-xs text-on-surface-variant">{rc.count.toLocaleString()} ratings</p>
        </div>
      </div>

      {/* ALS score */}
      {alsScore != null && (
        <div className="text-center">
          <p className="text-xs text-on-surface-variant uppercase tracking-widest mb-1">Predicted Score</p>
          <p className="text-lg font-bold text-primary">{(alsScore * 100).toFixed(0)}%</p>
        </div>
      )}

      {/* Genres */}
      <div>
        <p className="text-xs uppercase tracking-widest text-on-surface-variant font-label mb-2">Genres</p>
        <div className="flex flex-wrap gap-2">
          {movie.genres.map((g) => (
            <Pill key={g} text={g} highlighted={sharedGenres.has(g)} icon="category" />
          ))}
        </div>
      </div>

      {/* Cast */}
      {movie.cast_names.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-widest text-on-surface-variant font-label mb-2">Cast</p>
          <div className="flex flex-wrap gap-2">
            {movie.cast_names.slice(0, 10).map((a) => (
              <Pill key={a} text={a} highlighted={sharedActors.has(a)} icon="person" />
            ))}
          </div>
        </div>
      )}

      {/* Keywords */}
      {movie.keywords.length > 0 && (
        <div>
          <p className="text-xs uppercase tracking-widest text-on-surface-variant font-label mb-2">Keywords</p>
          <div className="flex flex-wrap gap-2">
            {movie.keywords.slice(0, 12).map((k) => (
              <Pill key={k} text={k} highlighted={sharedKeywords.has(k)} icon="tag" />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ---------- Main Compare page ---------- */
export default function Compare() {
  const [params, setParams] = useSearchParams();
  const { userId } = useUserId();
  const [movie1, setMovie1] = useState<AutocompleteSuggestion | null>(null);
  const [movie2, setMovie2] = useState<AutocompleteSuggestion | null>(null);
  const [comparison, setComparison] = useState<MovieComparisonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Sync URL params → state on mount
  useEffect(() => {
    const m1 = params.get("m1");
    const m2 = params.get("m2");
    if (m1 && !movie1) {
      const id = Number(m1);
      if (!Number.isNaN(id)) setMovie1({ id, title: `Movie #${id}`, year: null, poster_path: null });
    }
    if (m2 && !movie2) {
      const id = Number(m2);
      if (!Number.isNaN(id)) setMovie2({ id, title: `Movie #${id}`, year: null, poster_path: null });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch comparison when both movies are selected
  useEffect(() => {
    if (!movie1 || !movie2) {
      setComparison(null);
      return;
    }
    setLoading(true);
    setError("");
    compareMovies(movie1.id, movie2.id, userId)
      .then((res) => {
        setComparison(res);
        // Update selectors with full data from response
        setMovie1({ id: res.movie1.id, title: res.movie1.title, year: res.movie1.release_date ? Number(res.movie1.release_date.slice(0, 4)) : null, poster_path: res.movie1.poster_path });
        setMovie2({ id: res.movie2.id, title: res.movie2.title, year: res.movie2.release_date ? Number(res.movie2.release_date.slice(0, 4)) : null, poster_path: res.movie2.poster_path });
      })
      .catch((e) => setError(e?.detail || "Failed to compare movies"))
      .finally(() => setLoading(false));
  }, [movie1?.id, movie2?.id, userId]);

  const selectMovie1 = useCallback(
    (s: AutocompleteSuggestion) => {
      setMovie1(s);
      setParams((p) => { p.set("m1", String(s.id)); return p; });
    },
    [setParams],
  );

  const selectMovie2 = useCallback(
    (s: AutocompleteSuggestion) => {
      setMovie2(s);
      setParams((p) => { p.set("m2", String(s.id)); return p; });
    },
    [setParams],
  );

  const clearMovie1 = useCallback(() => {
    setMovie1(null);
    setComparison(null);
    setParams((p) => { p.delete("m1"); return p; });
  }, [setParams]);

  const clearMovie2 = useCallback(() => {
    setMovie2(null);
    setComparison(null);
    setParams((p) => { p.delete("m2"); return p; });
  }, [setParams]);

  const swap = useCallback(() => {
    const tmp1 = movie1;
    const tmp2 = movie2;
    setMovie1(tmp2);
    setMovie2(tmp1);
    setParams((p) => {
      if (tmp2) p.set("m1", String(tmp2.id)); else p.delete("m1");
      if (tmp1) p.set("m2", String(tmp1.id)); else p.delete("m2");
      return p;
    });
  }, [movie1, movie2, setParams]);

  const sharedGenres = new Set(comparison?.shared_genres || []);
  const sharedActors = new Set(comparison?.shared_actors || []);
  const sharedKeywords = new Set(comparison?.shared_keywords || []);

  return (
    <div className="min-h-screen bg-[#131314] text-on-surface">
      <TopNav />
      <main className="pt-28 pb-32 max-w-7xl mx-auto px-6">
        {/* Header */}
        <div className="mb-10">
          <h1 className="text-4xl md:text-5xl font-extrabold font-headline tracking-tighter text-glow">
            Compare Movies
          </h1>
          <p className="text-on-surface-variant mt-2">
            Pick two movies to compare side-by-side
          </p>
        </div>

        {/* Selectors */}
        <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-end mb-10">
          <MovieSelector
            label="Movie 1"
            selected={movie1}
            onSelect={selectMovie1}
            onClear={clearMovie1}
            excludeId={movie2?.id}
          />
          <button
            onClick={swap}
            disabled={!movie1 && !movie2}
            className="self-center p-3 rounded-full hover:bg-surface-container transition-colors disabled:opacity-30"
            title="Swap movies"
          >
            <span className="material-symbols-outlined text-primary text-2xl">swap_horiz</span>
          </button>
          <MovieSelector
            label="Movie 2"
            selected={movie2}
            onSelect={selectMovie2}
            onClear={clearMovie2}
            excludeId={movie1?.id}
          />
        </div>

        {/* Loading */}
        {loading && <LoadingSpinner text="Comparing movies..." />}

        {/* Error */}
        {error && <ErrorPanel message={error} onRetry={() => setError("")} />}

        {/* Comparison results */}
        {comparison && !loading && (
          <>
            {/* Side-by-side cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-10">
              <MovieColumn
                movie={comparison.movie1}
                rc={{ avg: comparison.rating_comparison.movie1_avg, count: comparison.rating_comparison.movie1_count }}
                side="left"
                sharedGenres={sharedGenres}
                sharedActors={sharedActors}
                sharedKeywords={sharedKeywords}
                alsScore={comparison.als_prediction?.movie1_score}
              />
              <MovieColumn
                movie={comparison.movie2}
                rc={{ avg: comparison.rating_comparison.movie2_avg, count: comparison.rating_comparison.movie2_count }}
                side="right"
                sharedGenres={sharedGenres}
                sharedActors={sharedActors}
                sharedKeywords={sharedKeywords}
                alsScore={comparison.als_prediction?.movie2_score}
              />
            </div>

            {/* Comparison panel */}
            <div className="glass-panel rounded-2xl p-8 space-y-8">
              <h3 className="text-2xl font-headline font-bold text-on-surface">Comparison</h3>

              {/* Embedding similarity */}
              {comparison.embedding_similarity != null && (
                <div>
                  <p className="text-xs uppercase tracking-widest text-on-surface-variant font-label mb-2">Content Similarity</p>
                  <div className="flex items-center gap-4">
                    <div className="flex-1 h-3 bg-surface-container rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-primary/60 to-primary rounded-full transition-all duration-700"
                        style={{ width: `${(comparison.embedding_similarity * 100).toFixed(0)}%` }}
                      />
                    </div>
                    <span className="text-on-surface font-bold text-lg min-w-[3rem] text-right">
                      {(comparison.embedding_similarity * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>
              )}

              {/* Same director */}
              {comparison.same_director && (
                <div className="flex items-center gap-2 text-primary">
                  <span className="material-symbols-outlined">movie_filter</span>
                  <span className="font-medium">Same director: {comparison.movie1.director}</span>
                </div>
              )}

              {/* Shared genres */}
              {comparison.shared_genres.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-widest text-on-surface-variant font-label mb-2">
                    Shared Genres ({comparison.shared_genres.length})
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {comparison.shared_genres.map((g) => (
                      <Pill key={g} text={g} highlighted icon="category" />
                    ))}
                  </div>
                </div>
              )}

              {/* Shared actors */}
              {comparison.shared_actors.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-widest text-on-surface-variant font-label mb-2">
                    Shared Cast ({comparison.shared_actors.length})
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {comparison.shared_actors.map((a) => (
                      <Pill key={a} text={a} highlighted icon="person" />
                    ))}
                  </div>
                </div>
              )}

              {/* Shared keywords */}
              {comparison.shared_keywords.length > 0 && (
                <div>
                  <p className="text-xs uppercase tracking-widest text-on-surface-variant font-label mb-2">
                    Shared Keywords ({comparison.shared_keywords.length})
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {comparison.shared_keywords.map((k) => (
                      <Pill key={k} text={k} highlighted icon="tag" />
                    ))}
                  </div>
                </div>
              )}

              {/* ALS preference */}
              {comparison.als_prediction && comparison.als_prediction.preferred_movie_id && (
                <div className="glass-card rounded-xl p-5 flex items-center gap-3">
                  <span className="material-symbols-outlined text-primary text-3xl">recommend</span>
                  <div>
                    <p className="text-sm text-on-surface-variant">Based on your taste</p>
                    <p className="text-on-surface font-bold">
                      You&apos;d likely prefer{" "}
                      <span className="text-primary">
                        {comparison.als_prediction.preferred_movie_id === comparison.movie1.id
                          ? comparison.movie1.title
                          : comparison.movie2.title}
                      </span>
                    </p>
                  </div>
                </div>
              )}

              {/* No overlap message */}
              {comparison.shared_genres.length === 0 &&
                comparison.shared_actors.length === 0 &&
                comparison.shared_keywords.length === 0 &&
                !comparison.same_director && (
                  <p className="text-on-surface-variant text-center py-4">
                    These movies have no overlapping genres, cast, keywords, or director.
                  </p>
                )}
            </div>
          </>
        )}

        {/* Empty state */}
        {!movie1 && !movie2 && !loading && (
          <div className="text-center py-20">
            <span className="material-symbols-outlined text-6xl text-on-surface-variant/30 mb-4 block">
              compare_arrows
            </span>
            <p className="text-on-surface-variant text-lg">
              Select two movies above to see how they compare
            </p>
          </div>
        )}
      </main>
      <BottomNav />
    </div>
  );
}
