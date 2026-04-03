import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getGlobalStats } from "../../api/stats";
import type { GlobalStatsResponse } from "../../api/types";
import ErrorPanel from "../../components/ErrorPanel";
import LoadingSpinner from "../../components/LoadingSpinner";

const TMDB_IMG = "https://image.tmdb.org/t/p/w300";

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

interface StatCardProps {
  icon: string;
  label: string;
  value: string;
}

function StatCard({ icon, label, value }: StatCardProps) {
  return (
    <div className="glass-card rounded-2xl p-6 flex flex-col items-center gap-2 text-center">
      <span className="material-symbols-outlined text-[#FFC107] text-3xl">
        {icon}
      </span>
      <span className="text-3xl md:text-4xl font-headline font-extrabold text-[#FFC107]">
        {value}
      </span>
      <span className="text-on-surface-variant font-label text-xs uppercase tracking-[0.15em]">
        {label}
      </span>
    </div>
  );
}

interface MovieHighlightProps {
  title: string;
  badge: string;
  movie: {
    id: number;
    title: string;
    poster_path: string | null;
    vote_average: number;
    genres: string[];
    release_date: string | null;
    rating_count: number;
    avg_user_rating?: number | null;
  };
}

function MovieHighlight({ title, badge, movie }: MovieHighlightProps) {
  return (
    <div className="glass-card rounded-2xl p-6 flex gap-5">
      <Link to={`/movies/${movie.id}`} className="shrink-0">
        {movie.poster_path ? (
          <img
            src={`${TMDB_IMG}${movie.poster_path}`}
            alt={movie.title}
            className="w-28 md:w-36 rounded-xl shadow-lg hover:scale-105 transition-transform"
          />
        ) : (
          <div className="w-28 md:w-36 h-44 md:h-52 rounded-xl bg-white/5 flex items-center justify-center">
            <span className="material-symbols-outlined text-4xl text-white/20">
              movie
            </span>
          </div>
        )}
      </Link>
      <div className="flex flex-col justify-center gap-2 min-w-0">
        <span className="text-on-surface-variant font-label text-xs uppercase tracking-[0.15em]">
          {title}
        </span>
        <Link
          to={`/movies/${movie.id}`}
          className="font-headline font-bold text-on-surface text-lg md:text-xl hover:text-[#FFC107] transition-colors truncate"
        >
          {movie.title}
        </Link>
        <div className="flex flex-wrap gap-1.5 mt-1">
          {movie.genres.slice(0, 3).map((g) => (
            <span
              key={g}
              className="text-[10px] uppercase tracking-wider font-medium bg-white/5 text-on-surface-variant rounded-full px-2.5 py-0.5"
            >
              {g}
            </span>
          ))}
        </div>
        {movie.release_date && (
          <span className="text-on-surface-variant text-xs">
            {movie.release_date.slice(0, 4)}
          </span>
        )}
        <span className="text-[#FFC107] font-headline font-bold text-sm mt-1">
          {badge}
        </span>
      </div>
    </div>
  );
}

export default function PlatformStatsTab() {
  const [data, setData] = useState<GlobalStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    getGlobalStats()
      .then(setData)
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  }, []);

  return (
    <>
      <header className="mb-10">
        <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
          Platform Stats
        </h1>
        <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
          A snapshot of the CineMatch community
        </p>
      </header>

      {loading && <LoadingSpinner />}
      {error && <ErrorPanel message={error} />}

      {data && (
        <>
          {/* Stat cards */}
          <section className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-12">
            <StatCard
              icon="movie"
              label="Total Movies"
              value={formatNumber(data.total_movies)}
            />
            <StatCard
              icon="group"
              label="Total Users"
              value={formatNumber(data.total_users)}
            />
            <StatCard
              icon="star"
              label="Total Ratings"
              value={formatNumber(data.total_ratings)}
            />
            <StatCard
              icon="grade"
              label="Average Rating"
              value={data.avg_rating.toFixed(1)}
            />
            <StatCard
              icon="calendar_today"
              label="Ratings This Week"
              value={formatNumber(data.ratings_this_week)}
            />
          </section>

          {/* Featured movies */}
          <section className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-12">
            {data.most_rated_movie && (
              <MovieHighlight
                title="Most Rated Movie"
                badge={`${formatNumber(data.most_rated_movie.rating_count)} ratings`}
                movie={data.most_rated_movie}
              />
            )}
            {data.highest_rated_movie && (
              <MovieHighlight
                title="Highest Rated Movie"
                badge={`${data.highest_rated_movie.avg_user_rating?.toFixed(1) ?? "—"} avg from ${formatNumber(data.highest_rated_movie.rating_count)} ratings`}
                movie={data.highest_rated_movie}
              />
            )}
          </section>

          {/* Most active user */}
          {data.most_active_user && (
            <section className="max-w-md">
              <div className="glass-card rounded-2xl p-6 flex items-center gap-4">
                <span className="material-symbols-outlined text-[#FFC107] text-4xl">
                  emoji_events
                </span>
                <div>
                  <span className="text-on-surface-variant font-label text-xs uppercase tracking-[0.15em] block mb-1">
                    Most Active User
                  </span>
                  <span className="font-headline font-bold text-on-surface text-lg">
                    User #{data.most_active_user.id}
                  </span>
                  <span className="text-[#FFC107] font-headline font-bold text-sm ml-3">
                    {formatNumber(data.most_active_user.rating_count)} ratings
                  </span>
                </div>
              </div>
            </section>
          )}
        </>
      )}
    </>
  );
}
