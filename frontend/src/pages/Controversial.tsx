import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getControversialMovies } from "../api/movies";
import type { ControversialMovieResult } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useDismissed } from "../hooks/useDismissed";
import { useRated } from "../hooks/useRated";
import { useWatchlist } from "../hooks/useWatchlist";

const MIN_RATINGS_OPTIONS = [
  { value: 50, label: "50+" },
  { value: 100, label: "100+" },
  { value: 250, label: "250+" },
  { value: 500, label: "500+" },
];

function getBarColor(rating: number): string {
  if (rating <= 2) return "#ef4444";
  if (rating <= 4) return "#f97316";
  if (rating <= 6) return "#a8a29e";
  if (rating <= 8) return "#2dd4bf";
  return "#22c55e";
}

export default function Controversial() {
  const [minRatings, setMinRatings] = useState(100);
  const [results, setResults] = useState<ControversialMovieResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } =
    useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();

  const fetchData = () => {
    setLoading(true);
    setError("");
    getControversialMovies({ min_ratings: minRatings, limit: 30 })
      .then((data) => {
        setResults(data.results);
        const ids = data.results.map((r) => r.movie.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        refreshRatingsForMovieIds(ids);
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchData();
  }, [minRatings]);

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <header className="mb-10">
            <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
              Controversial Movies
            </h1>
            <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
              Love-it-or-hate-it films with the most divided ratings
            </p>
          </header>

          {/* Filters */}
          <div className="mb-10">
            <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 block">
              Minimum Ratings
            </span>
            <div className="flex gap-2">
              {MIN_RATINGS_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setMinRatings(opt.value)}
                  className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                    minRatings === opt.value
                      ? "bg-primary-container text-on-primary-container shadow-md"
                      : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {loading && <LoadingSpinner text="Finding controversial films..." />}
          {error && <ErrorPanel message={error} onRetry={fetchData} />}

          {!loading && !error && (
            <>
              <p className="text-on-surface-variant text-sm mb-6">
                <span className="font-bold text-on-surface">
                  {results.length}
                </span>{" "}
                polarizing film{results.length !== 1 ? "s" : ""} found
              </p>
              <section className="grid grid-cols-1 xl:grid-cols-2 gap-8">
                {results.map((item) => (
                  <div
                    key={item.movie.id}
                    className="flex gap-5 p-5 rounded-2xl bg-surface-container-low border border-outline-variant/5"
                  >
                    {/* Movie card */}
                    <div className="w-40 flex-shrink-0">
                      <MovieCard
                        movie={item.movie}
                        isBookmarked={isInWatchlist(item.movie.id)}
                        onToggleBookmark={toggle}
                        isDismissed={isDismissed(item.movie.id)}
                        onDismiss={toggleDismiss}
                        userRating={getRating(item.movie.id)}
                      />
                    </div>

                    {/* Stats + histogram */}
                    <div className="flex-1 min-w-0">
                      {/* Stats row */}
                      <div className="flex flex-wrap gap-3 mb-4">
                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-surface-container-highest text-xs font-bold">
                          <span className="material-symbols-outlined text-sm">
                            star
                          </span>
                          {item.avg_rating.toFixed(1)} avg
                        </span>
                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-[#ef4444]/20 text-[#fca5a5] text-xs font-bold">
                          <span className="material-symbols-outlined text-sm">
                            whatshot
                          </span>
                          {item.stddev_rating.toFixed(2)} stddev
                        </span>
                        <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full bg-surface-container-highest text-xs font-bold text-on-surface-variant">
                          <span className="material-symbols-outlined text-sm">
                            group
                          </span>
                          {item.rating_count.toLocaleString()} ratings
                        </span>
                      </div>

                      {/* Histogram */}
                      <ResponsiveContainer width="100%" height={140}>
                        <BarChart
                          data={item.histogram}
                          margin={{
                            left: -15,
                            right: 5,
                            top: 0,
                            bottom: 0,
                          }}
                        >
                          <CartesianGrid
                            strokeDasharray="3 3"
                            stroke="rgba(255,255,255,0.05)"
                            vertical={false}
                          />
                          <XAxis
                            dataKey="rating"
                            tick={{
                              fill: "rgba(255,255,255,0.5)",
                              fontSize: 11,
                            }}
                            axisLine={false}
                            tickLine={false}
                          />
                          <YAxis
                            tick={{
                              fill: "rgba(255,255,255,0.5)",
                              fontSize: 10,
                            }}
                            axisLine={false}
                            tickLine={false}
                            allowDecimals={false}
                          />
                          <Tooltip
                            contentStyle={{
                              background: "#1C1B1F",
                              border: "1px solid rgba(255,255,255,0.1)",
                              borderRadius: 8,
                              color: "#E6E1E5",
                            }}
                            formatter={(value) => [value, "Ratings"]}
                            labelFormatter={(label) => `${label} stars`}
                          />
                          <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                            {item.histogram.map((entry) => (
                              <Cell
                                key={entry.rating}
                                fill={getBarColor(entry.rating)}
                              />
                            ))}
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                ))}
              </section>
            </>
          )}

          {!loading && !error && results.length === 0 && (
            <p className="text-center text-on-surface-variant text-lg py-20">
              No controversial movies found with these filters. Try lowering the
              minimum ratings threshold.
            </p>
          )}
        </div>
      </main>
      <BottomNav />
    </>
  );
}
