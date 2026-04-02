import { useEffect, useState } from "react";
import { getSeasonalMovies } from "../../api/movies";
import type { SeasonalMovieResult } from "../../api/types";
import ErrorPanel from "../../components/ErrorPanel";
import LoadingSpinner from "../../components/LoadingSpinner";
import MovieCard from "../../components/MovieCard";
import AddToListModal from "../../components/AddToListModal";
import { useDismissed } from "../../hooks/useDismissed";
import { useRated } from "../../hooks/useRated";
import { useMatchPredictions } from "../../hooks/useMatchPredictions";
import { useWatchlist } from "../../hooks/useWatchlist";

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function getMonthGradient(month: number): string {
  switch (month) {
    case 2: return "from-pink-900/40 to-red-900/30";
    case 5: case 6: case 7: case 8: return "from-amber-900/40 to-orange-900/30";
    case 10: return "from-purple-900/40 to-orange-900/30";
    case 12: return "from-blue-900/40 to-cyan-900/30";
    default: return "from-surface-container-highest/60 to-surface-container-high/40";
  }
}

export default function SeasonalTab() {
  const currentMonth = new Date().getMonth() + 1;
  const [activeMonth, setActiveMonth] = useState(currentMonth);
  const [results, setResults] = useState<SeasonalMovieResult[]>([]);
  const [seasonName, setSeasonName] = useState("");
  const [themeLabel, setThemeLabel] = useState("");
  const [genres, setGenres] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const { getMatchPercent, fetchMatchPercents } = useMatchPredictions();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  const fetchSeasonal = () => {
    setLoading(true);
    setError("");
    getSeasonalMovies(40, activeMonth)
      .then((data) => {
        setResults(data.results);
        setSeasonName(data.season_name);
        setThemeLabel(data.theme_label);
        setGenres(data.genres);
        const ids = data.results.map((r) => r.movie.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        refreshRatingsForMovieIds(ids);
        fetchMatchPercents(ids);
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchSeasonal();
  }, [activeMonth]);

  return (
    <>
      {/* Seasonal Banner */}
      <header className={`mb-10 rounded-2xl p-8 bg-gradient-to-br ${getMonthGradient(activeMonth)} border border-white/5`}>
        <div className="flex items-center gap-3 mb-2">
          <span className="material-symbols-outlined text-3xl text-[#FFC107]">
            calendar_month
          </span>
          <h1 className="font-headline font-extrabold text-on-surface tracking-tight text-3xl md:text-5xl">
            {themeLabel || "Seasonal Picks"}
          </h1>
        </div>
        <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
          {seasonName ? `${seasonName} picks` : "Time-aware recommendations"}
          {genres.length > 0 && (
            <span className="ml-3 normal-case tracking-normal text-on-surface-variant/70">
              {genres.join(" \u00B7 ")}
            </span>
          )}
        </p>
      </header>

      {/* Month Selector */}
      <div className="mb-10">
        <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-3 block">
          Month
        </span>
        <div className="flex gap-2 flex-wrap">
          {MONTHS.map((name, i) => {
            const month = i + 1;
            return (
              <button
                key={month}
                onClick={() => setActiveMonth(month)}
                className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                  activeMonth === month
                    ? "bg-primary-container text-on-primary-container shadow-md"
                    : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                }`}
              >
                {name.slice(0, 3)}
              </button>
            );
          })}
        </div>
      </div>

      {loading && <LoadingSpinner text="Finding seasonal picks..." />}
      {error && <ErrorPanel message={error} onRetry={fetchSeasonal} />}

      {!loading && !error && (
        <>
          <p className="text-on-surface-variant text-sm mb-6">
            <span className="font-bold text-on-surface">{results.length}</span>{" "}
            movie{results.length !== 1 ? "s" : ""} found
          </p>
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
                userRating={getRating(item.movie.id)}
                matchPercent={getMatchPercent(item.movie.id)}
              />
            ))}
          </section>
        </>
      )}

      {!loading && !error && results.length === 0 && (
        <p className="text-center text-on-surface-variant text-lg py-20">
          No seasonal picks found for {MONTHS[activeMonth - 1]}. Try a different month.
        </p>
      )}
      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
    </>
  );
}
