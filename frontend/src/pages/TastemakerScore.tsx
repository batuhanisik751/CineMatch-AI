import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type {
  TastemakerMovie,
  TastemakerScoreResponse,
  LeaderboardEntry,
  TastemakerLeaderboardResponse,
} from "../api/types";
import { getUserTastemakerScore, getTastemakerLeaderboard } from "../api/users";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";

function posterUrl(path: string | null, size = "w300") {
  return path ? `https://image.tmdb.org/t/p/${size}${path}` : null;
}

function labelColor(label: string): string {
  switch (label) {
    case "Trendsetter":
      return "text-[#fabd00]";
    case "Tastemaker":
      return "text-[#b4f0ff]";
    case "Early Adopter":
      return "text-[#ffb3ac]";
    default:
      return "text-on-surface-variant";
  }
}

function labelBgColor(label: string): string {
  switch (label) {
    case "Trendsetter":
      return "bg-[#fabd00]/15 border-[#fabd00]/30";
    case "Tastemaker":
      return "bg-[#b4f0ff]/15 border-[#b4f0ff]/30";
    case "Early Adopter":
      return "bg-[#ffb3ac]/15 border-[#ffb3ac]/30";
    default:
      return "bg-surface-container-high border-white/10";
  }
}

export default function TastemakerScore() {
  const { userId } = useUserId();
  const [scoreData, setScoreData] = useState<TastemakerScoreResponse | null>(
    null
  );
  const [leaderboard, setLeaderboard] =
    useState<TastemakerLeaderboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    Promise.all([
      getUserTastemakerScore(userId),
      getTastemakerLeaderboard(20),
    ])
      .then(([score, lb]) => {
        setScoreData(score);
        setLeaderboard(lb);
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  }, [userId]);

  const pct = scoreData ? Math.round(scoreData.score * 100) : 0;

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-24 pb-32 lg:pl-64">
        <div className="max-w-7xl mx-auto px-6 md:px-10">
          {/* Hero */}
          <div className="mb-12">
            <h1 className="text-5xl md:text-6xl font-extrabold font-headline tracking-tighter text-on-surface text-glow">
              YOUR TASTEMAKER SCORE
            </h1>
            <p className="text-on-surface-variant mt-3 text-lg">
              Do your early high ratings predict what the community will love?
            </p>
          </div>

          {loading && (
            <LoadingSpinner text="Calculating your tastemaker score..." />
          )}
          {error && <ErrorPanel message={error} />}

          {!loading && !error && scoreData && (
            <>
              {/* Score Card */}
              <div className="glass-card rounded-2xl p-8 md:p-12 mb-10 flex flex-col md:flex-row items-center gap-8">
                {/* Circular score */}
                <div className="relative w-48 h-48 flex-shrink-0">
                  <svg
                    viewBox="0 0 120 120"
                    className="w-full h-full -rotate-90"
                  >
                    <circle
                      cx="60"
                      cy="60"
                      r="52"
                      fill="none"
                      stroke="rgba(255,255,255,0.06)"
                      strokeWidth="10"
                    />
                    <circle
                      cx="60"
                      cy="60"
                      r="52"
                      fill="none"
                      stroke={
                        pct >= 70
                          ? "#fabd00"
                          : pct >= 50
                          ? "#b4f0ff"
                          : pct >= 30
                          ? "#ffb3ac"
                          : "#888"
                      }
                      strokeWidth="10"
                      strokeLinecap="round"
                      strokeDasharray={`${(pct / 100) * 327} 327`}
                      className="transition-all duration-1000"
                    />
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-4xl font-black font-headline text-on-surface">
                      {pct}%
                    </span>
                  </div>
                </div>

                {/* Score details */}
                <div className="flex-1 text-center md:text-left">
                  <div
                    className={`inline-block px-4 py-1.5 rounded-full border text-sm font-bold uppercase tracking-widest mb-4 ${labelBgColor(
                      scoreData.label
                    )} ${labelColor(scoreData.label)}`}
                  >
                    {scoreData.label}
                  </div>
                  <p className="text-on-surface-variant text-base mb-6">
                    {scoreData.total_early_high === 0
                      ? "Rate more movies early and generously to build your tastemaker reputation."
                      : `You rated ${scoreData.total_early_high} movies high before most others — ${scoreData.total_became_favorites} of those became community favorites.`}
                  </p>
                  <div className="flex gap-6 justify-center md:justify-start">
                    <div className="text-center">
                      <p className="text-2xl font-black font-headline text-on-surface">
                        {scoreData.total_early_high}
                      </p>
                      <p className="text-xs text-on-surface-variant uppercase tracking-widest">
                        Early High
                      </p>
                    </div>
                    <div className="text-center">
                      <p className="text-2xl font-black font-headline text-on-surface">
                        {scoreData.total_became_favorites}
                      </p>
                      <p className="text-xs text-on-surface-variant uppercase tracking-widest">
                        Became Favorites
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Evidence Movies */}
              {scoreData.evidence.length > 0 && (
                <section className="mb-14">
                  <h2 className="text-2xl font-bold font-headline text-on-surface mb-6">
                    YOUR PROOF
                  </h2>
                  <p className="text-on-surface-variant mb-6 text-sm">
                    Movies you loved early that the community later agreed with
                  </p>
                  <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-6">
                    {scoreData.evidence.map((item) => {
                      const poster = posterUrl(item.movie.poster_path);
                      const year = item.movie.release_date
                        ? new Date(item.movie.release_date).getFullYear()
                        : null;
                      return (
                        <div
                          key={item.movie.id}
                          className="group relative flex flex-col bg-surface-container-low rounded-xl overflow-hidden transition-all duration-300 glow-hover"
                        >
                          <Link to={`/movies/${item.movie.id}`}>
                            <div className="aspect-[2/3] overflow-hidden relative">
                              {poster ? (
                                <img
                                  src={poster}
                                  alt={item.movie.title}
                                  className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                                />
                              ) : (
                                <div className="w-full h-full bg-surface-container flex items-center justify-center">
                                  <span className="material-symbols-outlined text-5xl text-outline">
                                    movie
                                  </span>
                                </div>
                              )}
                              {/* Your rating badge */}
                              <div className="absolute top-4 right-4 bg-primary/90 backdrop-blur-md px-2.5 py-1 rounded flex items-center gap-1">
                                <span
                                  className="material-symbols-outlined text-[14px] text-on-primary"
                                  style={{
                                    fontVariationSettings: "'FILL' 1",
                                  }}
                                >
                                  star
                                </span>
                                <span className="text-xs font-bold text-on-primary">
                                  {item.user_rating}/10
                                </span>
                              </div>
                              {/* Early percentile badge */}
                              <div className="absolute top-4 left-4 bg-surface/80 backdrop-blur-md px-2 py-1 rounded">
                                <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
                                  Top{" "}
                                  {Math.max(
                                    1,
                                    Math.round(item.early_percentile * 100)
                                  )}
                                  % early
                                </span>
                              </div>
                            </div>
                            <div className="p-4 flex flex-col gap-2">
                              <div className="flex items-center gap-2">
                                {year && (
                                  <p className="text-xs font-label text-on-surface-variant">
                                    {year}
                                  </p>
                                )}
                              </div>
                              <h3 className="text-base font-headline font-bold text-on-surface leading-tight group-hover:text-primary transition-colors truncate">
                                {item.movie.title}
                              </h3>
                              <div className="flex flex-wrap gap-1">
                                {item.movie.genres.slice(0, 2).map((g) => (
                                  <span
                                    key={g}
                                    className="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 bg-surface-container-highest text-on-surface-variant rounded"
                                  >
                                    {g}
                                  </span>
                                ))}
                              </div>
                              <p className="text-xs text-on-surface-variant/60 mt-1 flex items-center gap-1">
                                <span className="material-symbols-outlined text-[14px]">
                                  groups
                                </span>
                                Community avg: {item.community_avg.toFixed(1)}
                              </p>
                            </div>
                          </Link>
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

              {/* Empty evidence state */}
              {scoreData.evidence.length === 0 && (
                <div className="text-center py-16 mb-14">
                  <span className="material-symbols-outlined text-6xl text-outline mb-4 block">
                    local_fire_department
                  </span>
                  <p className="text-on-surface-variant text-lg mb-2">
                    No tastemaker evidence yet
                  </p>
                  <p className="text-on-surface-variant/60 text-sm mb-6">
                    Rate movies you love early — before the crowd catches on.
                  </p>
                  <Link
                    to="/discover"
                    className="inline-block bg-primary-container/20 border border-primary-container/40 text-primary px-6 py-3 rounded-md font-bold hover:bg-primary-container hover:text-on-primary-container transition-all"
                  >
                    Discover Movies
                  </Link>
                </div>
              )}

              {/* Leaderboard */}
              {leaderboard && leaderboard.entries.length > 0 && (
                <section>
                  <h2 className="text-2xl font-bold font-headline text-on-surface mb-6">
                    TASTEMAKER LEADERBOARD
                  </h2>
                  <div className="glass-card rounded-2xl overflow-hidden">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-white/5">
                          <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                            Rank
                          </th>
                          <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                            User
                          </th>
                          <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                            Score
                          </th>
                          <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-widest text-on-surface-variant hidden sm:table-cell">
                            Early Picks
                          </th>
                          <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-widest text-on-surface-variant hidden sm:table-cell">
                            Hits
                          </th>
                          <th className="text-left px-6 py-4 text-xs font-bold uppercase tracking-widest text-on-surface-variant">
                            Label
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {leaderboard.entries.map((entry, i) => {
                          const isMe = entry.user_id === userId;
                          return (
                            <tr
                              key={entry.user_id}
                              className={`border-b border-white/5 transition-colors ${
                                isMe
                                  ? "bg-primary/5"
                                  : "hover:bg-surface-container-high/50"
                              }`}
                            >
                              <td className="px-6 py-4 text-on-surface font-bold">
                                {i <= 2 ? (
                                  <span
                                    className={
                                      i === 0
                                        ? "text-[#fabd00]"
                                        : i === 1
                                        ? "text-[#C0C0C0]"
                                        : "text-[#CD7F32]"
                                    }
                                  >
                                    #{i + 1}
                                  </span>
                                ) : (
                                  `#${i + 1}`
                                )}
                              </td>
                              <td className="px-6 py-4 text-on-surface">
                                <span className="flex items-center gap-2">
                                  <span className="material-symbols-outlined text-[18px] text-on-surface-variant">
                                    person
                                  </span>
                                  User {entry.user_id}
                                  {isMe && (
                                    <span className="text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 bg-primary/20 text-primary rounded">
                                      You
                                    </span>
                                  )}
                                </span>
                              </td>
                              <td className="px-6 py-4 text-on-surface font-bold font-headline">
                                {Math.round(entry.score * 100)}%
                              </td>
                              <td className="px-6 py-4 text-on-surface-variant hidden sm:table-cell">
                                {entry.total_early_high}
                              </td>
                              <td className="px-6 py-4 text-on-surface-variant hidden sm:table-cell">
                                {entry.total_became_favorites}
                              </td>
                              <td className="px-6 py-4">
                                <span
                                  className={`text-xs font-bold uppercase tracking-widest ${labelColor(
                                    entry.label
                                  )}`}
                                >
                                  {entry.label}
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}
            </>
          )}
        </div>
      </main>
      <BottomNav />
    </>
  );
}
