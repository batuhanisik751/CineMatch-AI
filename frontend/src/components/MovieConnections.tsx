import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { searchMovies, getMovieConnections, getMoviePath } from "../api/movies";
import type {
  MovieSummary,
  MovieConnectionsResponse,
  MoviePathResponse,
} from "../api/types";

const TYPE_COLORS: Record<string, string> = {
  actor: "bg-amber-500/20 text-amber-300 border-amber-500/30",
  director: "bg-blue-500/20 text-blue-300 border-blue-500/30",
  genre: "bg-green-500/20 text-green-300 border-green-500/30",
  keyword: "bg-purple-500/20 text-purple-300 border-purple-500/30",
};

const TYPE_ICONS: Record<string, string> = {
  actor: "person",
  director: "movie_filter",
  genre: "category",
  keyword: "tag",
};

function posterUrl(path: string | null, size = "w92") {
  return path ? `https://image.tmdb.org/t/p/${size}${path}` : null;
}

export default function MovieConnections({
  currentMovieId,
}: {
  currentMovieId: number;
}) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<MovieSummary[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [searching, setSearching] = useState(false);
  const [selectedMovie, setSelectedMovie] = useState<MovieSummary | null>(null);
  const [connections, setConnections] = useState<MovieConnectionsResponse | null>(null);
  const [path, setPath] = useState<MoviePathResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();
  const wrapperRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
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
        setShowDropdown(false);
        return;
      }
      setSearching(true);
      debounceRef.current = setTimeout(() => {
        searchMovies(q.trim(), 8)
          .then((res) => {
            setResults(res.results.filter((m) => m.id !== currentMovieId));
            setShowDropdown(true);
          })
          .catch(() => setResults([]))
          .finally(() => setSearching(false));
      }, 300);
    },
    [currentMovieId],
  );

  const handleSelect = useCallback(
    (movie: MovieSummary) => {
      setSelectedMovie(movie);
      setQuery(movie.title);
      setShowDropdown(false);
      setLoading(true);
      setError("");
      setConnections(null);
      setPath(null);

      Promise.all([
        getMovieConnections(currentMovieId, movie.id),
        getMoviePath(currentMovieId, movie.id),
      ])
        .then(([conn, p]) => {
          setConnections(conn);
          setPath(p);
        })
        .catch((e) => setError(e.detail || e.message || "Failed to load connections"))
        .finally(() => setLoading(false));
    },
    [currentMovieId],
  );

  const handleClear = () => {
    setQuery("");
    setSelectedMovie(null);
    setConnections(null);
    setPath(null);
    setError("");
    setResults([]);
  };

  return (
    <section className="bg-surface-container-lowest py-16">
      <div className="max-w-7xl mx-auto px-8">
        <div className="flex items-center gap-3 mb-8">
          <span className="material-symbols-outlined text-3xl text-primary">hub</span>
          <h3 className="text-3xl font-headline font-extrabold text-on-surface tracking-tight">
            Six Degrees
          </h3>
        </div>
        <p className="text-on-surface-variant mb-6 max-w-2xl">
          Discover how two movies are connected through shared actors, directors, genres, and keywords.
        </p>

        {/* Search input */}
        <div ref={wrapperRef} className="relative max-w-md mb-8">
          <div className="relative">
            <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-outline text-xl">
              search
            </span>
            <input
              type="text"
              value={query}
              onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search for a movie to compare..."
              className="w-full pl-10 pr-10 py-3 rounded-xl bg-surface-container border border-outline-variant/20 text-on-surface placeholder:text-outline focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
            />
            {(query || selectedMovie) && (
              <button
                onClick={handleClear}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-outline hover:text-on-surface transition-colors"
              >
                <span className="material-symbols-outlined text-xl">close</span>
              </button>
            )}
          </div>
          {searching && (
            <div className="absolute right-12 top-1/2 -translate-y-1/2">
              <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {/* Dropdown */}
          {showDropdown && results.length > 0 && (
            <div className="absolute z-50 w-full mt-2 rounded-xl bg-surface-container border border-outline-variant/20 shadow-2xl overflow-hidden max-h-80 overflow-y-auto">
              {results.map((m) => {
                const p = posterUrl(m.poster_path);
                return (
                  <button
                    key={m.id}
                    onClick={() => handleSelect(m)}
                    className="w-full flex items-center gap-3 px-4 py-3 hover:bg-surface-container-high transition-colors text-left"
                  >
                    {p ? (
                      <img src={p} alt="" className="w-10 h-14 rounded object-cover shrink-0" />
                    ) : (
                      <div className="w-10 h-14 rounded bg-surface-container-high flex items-center justify-center shrink-0">
                        <span className="material-symbols-outlined text-outline text-lg">movie</span>
                      </div>
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-on-surface truncate">{m.title}</p>
                      <p className="text-xs text-on-surface-variant">
                        {m.genres.slice(0, 2).join(" · ")}
                        {m.release_date ? ` · ${m.release_date.slice(0, 4)}` : ""}
                      </p>
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex items-center gap-3 text-on-surface-variant py-8">
            <div className="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
            Finding connections...
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="text-error text-sm py-4">{error}</div>
        )}

        {/* Results */}
        {!loading && connections && selectedMovie && (
          <div className="space-y-8">
            {/* Direct connections */}
            <div className="glass-panel rounded-2xl p-6">
              <h4 className="text-lg font-bold text-on-surface mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-primary">link</span>
                Direct Connections
                <span className="text-sm font-normal text-on-surface-variant">
                  ({connections.connection_count} found)
                </span>
              </h4>
              {connections.connections.length === 0 ? (
                <p className="text-on-surface-variant text-sm">No direct connections found between these movies.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {connections.connections.map((c, i) => (
                    <span
                      key={`${c.type}-${c.value}-${i}`}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border ${TYPE_COLORS[c.type] || "bg-surface-container text-on-surface border-outline-variant/30"}`}
                    >
                      <span className="material-symbols-outlined text-[16px]">
                        {TYPE_ICONS[c.type] || "circle"}
                      </span>
                      {c.value}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Path */}
            {path && (
              <div className="glass-panel rounded-2xl p-6">
                <h4 className="text-lg font-bold text-on-surface mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary">route</span>
                  Shortest Path
                  {path.found && (
                    <span className="text-sm font-normal text-on-surface-variant">
                      ({path.degrees} degree{path.degrees !== 1 ? "s" : ""} of separation)
                    </span>
                  )}
                </h4>
                {!path.found ? (
                  <p className="text-on-surface-variant text-sm">
                    No path found within 6 degrees of separation.
                  </p>
                ) : (
                  <div className="flex items-center gap-2 overflow-x-auto pb-4 hide-scrollbar">
                    {path.path.map((step, i) => {
                      const p = posterUrl(step.movie.poster_path);
                      return (
                        <div key={step.movie.id} className="flex items-center gap-2 shrink-0">
                          {i > 0 && step.linked_by && (
                            <div className="flex flex-col items-center gap-1 px-2">
                              <div className="w-8 h-px bg-primary" />
                              <span className="text-[10px] text-primary font-medium whitespace-nowrap max-w-24 truncate">
                                {step.linked_by}
                              </span>
                              <div className="w-8 h-px bg-primary" />
                            </div>
                          )}
                          <Link
                            to={`/movies/${step.movie.id}`}
                            className="flex flex-col items-center gap-2 group w-24"
                          >
                            <div className="w-16 h-24 rounded-lg overflow-hidden shadow-md group-hover:ring-2 ring-primary transition-all">
                              {p ? (
                                <img src={p} alt="" className="w-full h-full object-cover" />
                              ) : (
                                <div className="w-full h-full bg-surface-container flex items-center justify-center">
                                  <span className="material-symbols-outlined text-outline">movie</span>
                                </div>
                              )}
                            </div>
                            <span className="text-xs text-on-surface text-center leading-tight line-clamp-2 group-hover:text-primary transition-colors">
                              {step.movie.title}
                            </span>
                          </Link>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
