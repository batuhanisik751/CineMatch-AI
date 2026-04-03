import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getDismissals, undismissMovie } from "../../api/dismissals";
import { exportRatings, getUserRatings } from "../../api/ratings";
import type { AchievementResponse, AffinitiesResponse, AffinityEntry, DismissalItemResponse, RatingComparisonResponse, RatingResponse, StreakResponse, TasteProfileResponse, UserResponse, UserStatsResponse } from "../../api/types";
import { getRatingComparison, getTasteProfile, getUser, getUserAchievements, getUserAffinities, getUserStats, getUserStreaks } from "../../api/users";
import ErrorPanel from "../../components/ErrorPanel";
import ImportRatingsModal from "../../components/ImportRatingsModal";
import { useUserId } from "../../hooks/useUserId";

export default function OverviewTab() {
  const { userId } = useUserId();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [ratings, setRatings] = useState<RatingResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<UserStatsResponse | null>(null);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [dismissedItems, setDismissedItems] = useState<DismissalItemResponse[]>([]);
  const [dismissedTotal, setDismissedTotal] = useState(0);
  const [showDismissed, setShowDismissed] = useState(false);
  const [tasteProfile, setTasteProfile] = useState<TasteProfileResponse | null>(null);
  const [ratingComparison, setRatingComparison] = useState<RatingComparisonResponse | null>(null);
  const [affinities, setAffinities] = useState<AffinitiesResponse | null>(null);
  const [streaks, setStreaks] = useState<StreakResponse | null>(null);
  const [achievements, setAchievements] = useState<AchievementResponse | null>(null);
  const [expandedAffinity, setExpandedAffinity] = useState<string | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);
  const [exporting, setExporting] = useState(false);
  const limit = 20;

  const fetchUser = async () => {
    setLoading(true);
    setError("");
    try {
      const [u, r, s] = await Promise.all([
        getUser(userId),
        getUserRatings(userId, 0, limit),
        getUserStats(userId),
      ]);
      setUser(u);
      setRatings(r.ratings);
      setTotal(r.total);
      setStats(s);
      setOffset(0);
      // Fetch dismissed movies count (best-effort)
      getDismissals(userId, 0, 20)
        .then((d) => { setDismissedItems(d.items); setDismissedTotal(d.total); })
        .catch(() => {});
      // Fetch taste profile (best-effort)
      getTasteProfile(userId)
        .then((tp) => setTasteProfile(tp))
        .catch(() => {});
      // Fetch rating comparison (best-effort)
      getRatingComparison(userId)
        .then((rc) => setRatingComparison(rc))
        .catch(() => {});
      // Fetch affinities (best-effort)
      getUserAffinities(userId)
        .then((a) => setAffinities(a))
        .catch(() => {});
      // Fetch streaks (best-effort)
      getUserStreaks(userId)
        .then((s) => setStreaks(s))
        .catch(() => {});
      // Fetch achievements (best-effort)
      getUserAchievements(userId)
        .then((a) => setAchievements(a))
        .catch(() => {});
    } catch {
      // User hasn't rated anything yet — that's fine, not an error
      setUser(null);
      setRatings([]);
      setTotal(0);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

  const handleExport = async () => {
    setExporting(true);
    try {
      await exportRatings(userId);
    } catch {
      setError("Failed to export ratings.");
    } finally {
      setExporting(false);
    }
  };

  const handleImportSuccess = () => {
    fetchUser();
  };

  const changePage = async (newOffset: number) => {
    if (!user) return;
    try {
      const r = await getUserRatings(user.id, newOffset, limit);
      setRatings(r.ratings);
      setTotal(r.total);
      setOffset(newOffset);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load ratings";
      setError(msg);
    }
  };

  const stars = (rating: number) => {
    return (
      <div className="flex items-center justify-center gap-1 text-primary-fixed-dim">
        <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
        <span className="text-sm font-bold text-on-surface">{rating}/10</span>
      </div>
    );
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <>
      <div className="flex flex-col gap-12">
        {/* Profile Header / Lookup */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
          <div className="lg:col-span-1 flex flex-col gap-6">
            <div className="p-8 rounded-xl glass-panel border border-outline-variant/10 shadow-2xl">
              <h2 className="font-headline text-2xl font-extrabold mb-6 tracking-tight">Your Profile</h2>
              <div className="flex flex-col gap-4">
                <label className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/70">Your Member ID</label>
                <div className="w-full bg-surface-container-lowest border border-outline-variant/20 rounded-lg px-4 py-4 font-mono text-primary-fixed text-lg">
                  USR-{userId}
                </div>
                <p className="text-xs text-on-surface-variant/60">
                  Your ID is automatically assigned and saved to this browser.
                </p>
              </div>
            </div>
          </div>
          {user && (
            <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-6 rounded-xl bg-surface-container-low flex flex-col gap-2">
                <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Movies Rated</span>
                <span className="font-headline text-2xl font-bold text-on-surface">{stats?.total_ratings ?? total}</span>
              </div>
              <div className="p-6 rounded-xl bg-surface-container-low flex flex-col gap-2">
                <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Avg Rating</span>
                <span className="font-headline text-2xl font-bold text-on-surface">
                  {stats ? stats.average_rating.toFixed(1) : "—"}
                </span>
              </div>
              <div className="p-6 rounded-xl bg-surface-container-low flex flex-col gap-2">
                <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Member Since</span>
                <span className="font-headline text-2xl font-bold text-on-surface">
                  {new Date(user.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                </span>
              </div>
              <div className="md:col-span-3 p-8 rounded-xl bg-gradient-to-r from-surface-container to-surface-container-highest flex items-center justify-between border-l-4 border-primary">
                <div>
                  <h3 className="font-headline text-xl font-bold text-primary mb-1">CineMatch AI Status</h3>
                  <p className="text-on-surface-variant text-sm">Active screening preferences and historical data are synchronized.</p>
                </div>
                <span className="material-symbols-outlined text-4xl text-primary-fixed-dim" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
              </div>
            </div>
          )}
          {!user && !loading && (
            <div className="lg:col-span-2 flex items-center justify-center p-12 rounded-xl bg-surface-container-low border border-outline-variant/10">
              <div className="text-center space-y-4">
                <span className="material-symbols-outlined text-5xl text-outline/40">movie_filter</span>
                <p className="text-on-surface-variant">You haven't rated any movies yet. Browse and rate movies to build your profile!</p>
                <button
                  onClick={() => setShowImportModal(true)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full text-sm font-bold bg-primary/15 text-primary hover:bg-primary/25 transition-all"
                >
                  <span className="material-symbols-outlined text-base">upload_file</span>
                  Import from Letterboxd / IMDb
                </button>
              </div>
            </div>
          )}
        </section>

        {loading && <div className="flex justify-center py-12"><div className="w-12 h-12 border-4 border-primary-container/20 border-t-primary-container rounded-full animate-spin" /></div>}
        {error && <ErrorPanel message={error} />}

        {/* Rating Streaks & Milestones */}
        {streaks && (
          <section className="flex flex-col gap-6">
            <h2 className="font-headline text-3xl font-black italic tracking-tighter text-on-surface">Rating Streaks</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-6 rounded-xl bg-surface-container-low flex flex-col gap-2">
                <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Current Streak</span>
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-2xl text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>local_fire_department</span>
                  <span className="font-headline text-2xl font-bold text-on-surface">{streaks.current_streak} {streaks.current_streak === 1 ? "day" : "days"}</span>
                </div>
              </div>
              <div className="p-6 rounded-xl bg-surface-container-low flex flex-col gap-2">
                <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Longest Streak</span>
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-2xl text-tertiary" style={{ fontVariationSettings: "'FILL' 1" }}>emoji_events</span>
                  <span className="font-headline text-2xl font-bold text-on-surface">{streaks.longest_streak} {streaks.longest_streak === 1 ? "day" : "days"}</span>
                </div>
              </div>
            </div>
            <div className="flex flex-wrap gap-3">
              {streaks.milestones.map((m) => (
                <div
                  key={m.threshold}
                  className={`px-4 py-2 rounded-full flex items-center gap-2 text-sm font-bold transition-all ${
                    m.reached
                      ? "bg-primary/20 text-primary"
                      : "bg-surface-container text-on-surface-variant/40"
                  }`}
                >
                  <span
                    className="material-symbols-outlined text-base"
                    style={{ fontVariationSettings: m.reached ? "'FILL' 1" : "'FILL' 0" }}
                  >
                    {m.reached ? "check_circle" : "circle"}
                  </span>
                  {m.label}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Achievements */}
        {achievements && achievements.unlocked_count > 0 && (
          <section className="glass-card p-8 rounded-xl">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-3xl text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>emoji_events</span>
                <h2 className="font-headline text-2xl font-extrabold tracking-tight text-on-surface">Achievements</h2>
              </div>
              <Link to="/activity/achievements" className="text-sm text-primary hover:underline">
                View all {achievements.unlocked_count}/{achievements.total_count}
              </Link>
            </div>
            <div className="flex flex-wrap gap-3">
              {achievements.badges
                .filter((b) => b.unlocked)
                .map((b) => (
                  <div
                    key={b.id}
                    className="px-4 py-2 rounded-full flex items-center gap-2 text-sm font-bold bg-primary/20 text-primary"
                  >
                    <span
                      className="material-symbols-outlined text-base"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      {b.icon}
                    </span>
                    {b.name}
                  </div>
                ))}
            </div>
          </section>
        )}

        {/* Taste Evolution Link */}
        <Link
          to="/profile/taste-evolution"
          className="flex items-center gap-4 p-6 rounded-xl bg-surface-container-low hover:bg-surface-container transition-all group"
        >
          <span className="material-symbols-outlined text-3xl text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>timeline</span>
          <div className="flex-1">
            <h3 className="font-headline text-lg font-bold text-on-surface">Taste Evolution</h3>
            <p className="text-sm text-on-surface-variant">See how your genre preferences have shifted over time</p>
          </div>
          <span className="material-symbols-outlined text-on-surface-variant group-hover:translate-x-1 transition-transform">arrow_forward</span>
        </Link>

        {/* Taste Profile */}
        {tasteProfile && tasteProfile.insights.length > 0 && (
          <section className="p-8 rounded-xl bg-gradient-to-r from-surface-container to-surface-container-highest border border-outline-variant/10 shadow-lg">
            <div className="flex items-center gap-3 mb-6">
              <span className="material-symbols-outlined text-3xl text-primary" style={{ fontVariationSettings: "'FILL' 1" }}>auto_awesome</span>
              <h2 className="font-headline text-2xl font-extrabold tracking-tight text-on-surface">Your Taste Profile</h2>
            </div>
            <div className="flex flex-col gap-4">
              {tasteProfile.insights.map((insight) => (
                <div key={insight.key} className="flex items-start gap-4">
                  <span className="material-symbols-outlined text-xl text-primary-fixed-dim mt-0.5" style={{ fontVariationSettings: "'FILL' 1" }}>{insight.icon}</span>
                  <p className="text-on-surface font-body text-base leading-relaxed">{insight.text}</p>
                </div>
              ))}
            </div>
            {tasteProfile.llm_summary && (
              <div className="mt-6 pt-6 border-t border-outline-variant/10">
                <p className="text-on-surface-variant font-body text-sm italic leading-relaxed">{tasteProfile.llm_summary}</p>
              </div>
            )}
          </section>
        )}

        {/* Rating Comparison */}
        {ratingComparison && ratingComparison.total_rated > 0 && (
          <section className="flex flex-col gap-6">
            <div>
              <h2 className="font-headline text-3xl font-black italic tracking-tighter text-on-surface mb-2">You vs. Community</h2>
              <p className="text-on-surface-variant font-body">How your ratings compare to everyone else's.</p>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-6 rounded-xl bg-surface-container-low flex flex-col gap-2">
                <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Your Average</span>
                <span className="font-headline text-2xl font-bold text-on-surface">{ratingComparison.user_avg.toFixed(1)}</span>
              </div>
              <div className="p-6 rounded-xl bg-surface-container-low flex flex-col gap-2">
                <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Community Average</span>
                <span className="font-headline text-2xl font-bold text-on-surface">{ratingComparison.community_avg.toFixed(1)}</span>
              </div>
              <div className="p-6 rounded-xl bg-surface-container-low flex flex-col gap-2">
                <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Agreement</span>
                <span className="font-headline text-2xl font-bold text-on-surface">{ratingComparison.agreement_pct.toFixed(0)}%</span>
              </div>
            </div>

            {/* Overrated / Underrated */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Most Overrated */}
              {ratingComparison.most_overrated.length > 0 && (
                <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 mb-6 flex items-center gap-2">
                    <span className="material-symbols-outlined text-base text-tertiary">arrow_upward</span>
                    You Rated Higher
                  </h3>
                  <div className="flex flex-col gap-4">
                    {ratingComparison.most_overrated.map((m) => (
                      <Link key={m.movie_id} to={`/movies/${m.movie_id}`} className="flex items-center gap-4 group">
                        <div className="w-10 h-14 rounded overflow-hidden bg-surface-container flex-shrink-0">
                          {m.poster_path ? (
                            <img src={`https://image.tmdb.org/t/p/w92${m.poster_path}`} alt={m.title} className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <span className="material-symbols-outlined text-sm text-outline">movie</span>
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-headline font-bold text-on-surface truncate group-hover:text-primary transition-colors">{m.title}</p>
                          <p className="text-xs text-on-surface-variant">You: {m.user_rating}/10 &middot; Community: {m.community_avg.toFixed(1)}</p>
                        </div>
                        <span className="text-sm font-bold text-tertiary flex-shrink-0">+{m.difference.toFixed(1)}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Most Underrated */}
              {ratingComparison.most_underrated.length > 0 && (
                <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 mb-6 flex items-center gap-2">
                    <span className="material-symbols-outlined text-base text-error">arrow_downward</span>
                    You Rated Lower
                  </h3>
                  <div className="flex flex-col gap-4">
                    {ratingComparison.most_underrated.map((m) => (
                      <Link key={m.movie_id} to={`/movies/${m.movie_id}`} className="flex items-center gap-4 group">
                        <div className="w-10 h-14 rounded overflow-hidden bg-surface-container flex-shrink-0">
                          {m.poster_path ? (
                            <img src={`https://image.tmdb.org/t/p/w92${m.poster_path}`} alt={m.title} className="w-full h-full object-cover" />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center">
                              <span className="material-symbols-outlined text-sm text-outline">movie</span>
                            </div>
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-headline font-bold text-on-surface truncate group-hover:text-primary transition-colors">{m.title}</p>
                          <p className="text-xs text-on-surface-variant">You: {m.user_rating}/10 &middot; Community: {m.community_avg.toFixed(1)}</p>
                        </div>
                        <span className="text-sm font-bold text-error flex-shrink-0">{m.difference.toFixed(1)}</span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Analytics Dashboard */}
        {stats && stats.total_ratings > 0 && (
          <section className="flex flex-col gap-6">
            <div>
              <div className="flex items-center justify-between">
                <h2 className="font-headline text-3xl font-black italic tracking-tighter text-on-surface mb-2">Analytics</h2>
                <Link to="/activity/diary" className="flex items-center gap-1.5 text-sm font-bold text-primary hover:text-primary/80 transition-colors">
                  <span className="material-symbols-outlined text-base">calendar_month</span>
                  Film Diary
                </Link>
              </div>
              <p className="text-on-surface-variant font-body">Insights from your viewing history and ratings.</p>
            </div>

            {/* Rating Distribution */}
            <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
              <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 mb-6">Rating Distribution</h3>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={stats.rating_distribution} margin={{ left: -10, right: 10, top: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="rating" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{ background: "#1C1B1F", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#E6E1E5" }}
                    formatter={(value) => [value, "Ratings"]}
                    labelFormatter={(label) => `${label} stars`}
                  />
                  <Bar dataKey="count" fill="#D0BCFF" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Genre Affinity Radar */}
            {stats.genre_distribution.length > 0 && (
              <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
                <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 mb-6">Genre Affinity</h3>
                <ResponsiveContainer width="100%" height={350}>
                  <RadarChart data={stats.genre_distribution.slice(0, 8)} cx="50%" cy="50%" outerRadius="75%">
                    <PolarGrid stroke="rgba(255,255,255,0.1)" />
                    <PolarAngleAxis dataKey="genre" tick={{ fill: "rgba(255,255,255,0.7)", fontSize: 12 }} />
                    <PolarRadiusAxis tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 10 }} domain={[0, "auto"]} />
                    <Tooltip
                      contentStyle={{ background: "#1C1B1F", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#E6E1E5" }}
                      formatter={(value) => [`${value}%`, "Affinity"]}
                    />
                    <Radar name="Genre Affinity" dataKey="percentage" stroke="#D0BCFF" fill="#D0BCFF" fillOpacity={0.3} />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Row 2: Top Directors + Top Actors */}
            {(stats.top_directors.length > 0 || stats.top_actors.length > 0) && (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Top Directors */}
                {stats.top_directors.length > 0 && (
                  <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 mb-6">Top Directors</h3>
                    <ResponsiveContainer width="100%" height={Math.max(200, stats.top_directors.length * 36)}>
                      <BarChart data={stats.top_directors} layout="vertical" margin={{ left: 10, right: 30, top: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                        <XAxis type="number" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                        <YAxis type="category" dataKey="name" width={120} tick={{ fill: "rgba(255,255,255,0.7)", fontSize: 12 }} axisLine={false} tickLine={false} />
                        <Tooltip
                          contentStyle={{ background: "#1C1B1F", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#E6E1E5" }}
                          formatter={(value) => [value, "Movies Rated"]}
                        />
                        <Bar dataKey="count" fill="#CCC2DC" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Top Actors */}
                {stats.top_actors.length > 0 && (
                  <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
                    <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 mb-6">Top Actors</h3>
                    <ResponsiveContainer width="100%" height={Math.max(200, stats.top_actors.length * 36)}>
                      <BarChart data={stats.top_actors} layout="vertical" margin={{ left: 10, right: 30, top: 0, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" horizontal={false} />
                        <XAxis type="number" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                        <YAxis type="category" dataKey="name" width={120} tick={{ fill: "rgba(255,255,255,0.7)", fontSize: 12 }} axisLine={false} tickLine={false} />
                        <Tooltip
                          contentStyle={{ background: "#1C1B1F", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#E6E1E5" }}
                          formatter={(value) => [value, "Movies Rated"]}
                        />
                        <Bar dataKey="count" fill="#EFB8C8" radius={[0, 4, 4, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>
            )}

            {/* Row 3: Rating Timeline */}
            {stats.rating_timeline.length > 1 && (
              <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
                <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 mb-6">Rating Timeline</h3>
                <ResponsiveContainer width="100%" height={250}>
                  <AreaChart data={stats.rating_timeline} margin={{ left: -10, right: 10, top: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="timelineGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#D0BCFF" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#D0BCFF" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                    <XAxis dataKey="month" tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                    <Tooltip
                      contentStyle={{ background: "#1C1B1F", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8, color: "#E6E1E5" }}
                      formatter={(value) => [value, "Ratings"]}
                    />
                    <Area type="monotone" dataKey="count" stroke="#D0BCFF" fill="url(#timelineGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            )}
          </section>
        )}

        {/* Director & Actor Affinities */}
        {affinities && (affinities.directors.length > 0 || affinities.actors.length > 0) && (
          <section className="flex flex-col gap-6">
            <div>
              <h2 className="font-headline text-3xl font-black italic tracking-tighter text-on-surface mb-2">Director & Actor Affinities</h2>
              <p className="text-on-surface-variant font-body">Your favorite filmmakers ranked by rating enthusiasm.</p>
            </div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Directors */}
              {affinities.directors.length > 0 && (
                <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 mb-6 flex items-center gap-2">
                    <span className="material-symbols-outlined text-base text-primary-fixed-dim" style={{ fontVariationSettings: "'FILL' 1" }}>movie</span>
                    Directors
                  </h3>
                  <div className="flex flex-col gap-3">
                    {affinities.directors.map((entry: AffinityEntry) => {
                      const key = `director-${entry.name}`;
                      const isExpanded = expandedAffinity === key;
                      const maxScore = affinities.directors[0]?.weighted_score ?? 1;
                      return (
                        <div key={key}>
                          <button onClick={() => setExpandedAffinity(isExpanded ? null : key)} className="w-full text-left group">
                            <div className="flex items-center gap-3">
                              <span className="text-sm font-headline font-bold text-on-surface truncate w-28 flex-shrink-0 group-hover:text-primary transition-colors">{entry.name}</span>
                              <div className="flex-1 h-5 bg-surface-container rounded-full overflow-hidden">
                                <div className="h-full bg-[#CCC2DC] rounded-full transition-all duration-500" style={{ width: `${(entry.weighted_score / maxScore) * 100}%` }} />
                              </div>
                              <span className="text-xs font-bold text-on-surface-variant flex-shrink-0 w-10 text-right">{entry.weighted_score}</span>
                              <span className="text-xs text-on-surface-variant/60 flex-shrink-0 w-16 text-right">{entry.avg_rating.toFixed(1)} avg</span>
                              <span className="text-xs text-on-surface-variant/60 flex-shrink-0">{entry.count} films</span>
                              <span className={`material-symbols-outlined text-sm text-on-surface-variant transition-transform ${isExpanded ? "rotate-180" : ""}`}>expand_more</span>
                            </div>
                          </button>
                          {isExpanded && (
                            <div className="mt-2 ml-2 flex flex-col gap-2 pl-4 border-l-2 border-outline-variant/10">
                              {entry.films_rated.map((f) => (
                                <Link key={f.movie_id} to={`/movies/${f.movie_id}`} className="flex items-center gap-3 group/film">
                                  <div className="w-8 h-12 rounded overflow-hidden bg-surface-container flex-shrink-0">
                                    {f.poster_path ? (
                                      <img src={`https://image.tmdb.org/t/p/w92${f.poster_path}`} alt={f.title} className="w-full h-full object-cover" />
                                    ) : (
                                      <div className="w-full h-full flex items-center justify-center"><span className="material-symbols-outlined text-xs text-outline">movie</span></div>
                                    )}
                                  </div>
                                  <span className="text-sm text-on-surface truncate group-hover/film:text-primary transition-colors">{f.title}</span>
                                  <span className="ml-auto text-xs font-bold text-primary-fixed-dim flex-shrink-0">{f.rating}/10</span>
                                </Link>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Actors */}
              {affinities.actors.length > 0 && (
                <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
                  <h3 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 mb-6 flex items-center gap-2">
                    <span className="material-symbols-outlined text-base text-tertiary" style={{ fontVariationSettings: "'FILL' 1" }}>person</span>
                    Actors
                  </h3>
                  <div className="flex flex-col gap-3">
                    {affinities.actors.map((entry: AffinityEntry) => {
                      const key = `actor-${entry.name}`;
                      const isExpanded = expandedAffinity === key;
                      const maxScore = affinities.actors[0]?.weighted_score ?? 1;
                      return (
                        <div key={key}>
                          <button onClick={() => setExpandedAffinity(isExpanded ? null : key)} className="w-full text-left group">
                            <div className="flex items-center gap-3">
                              <span className="text-sm font-headline font-bold text-on-surface truncate w-28 flex-shrink-0 group-hover:text-primary transition-colors">{entry.name}</span>
                              <div className="flex-1 h-5 bg-surface-container rounded-full overflow-hidden">
                                <div className="h-full bg-[#EFB8C8] rounded-full transition-all duration-500" style={{ width: `${(entry.weighted_score / maxScore) * 100}%` }} />
                              </div>
                              <span className="text-xs font-bold text-on-surface-variant flex-shrink-0 w-10 text-right">{entry.weighted_score}</span>
                              <span className="text-xs text-on-surface-variant/60 flex-shrink-0 w-16 text-right">{entry.avg_rating.toFixed(1)} avg</span>
                              <span className="text-xs text-on-surface-variant/60 flex-shrink-0">{entry.count} films</span>
                              <span className={`material-symbols-outlined text-sm text-on-surface-variant transition-transform ${isExpanded ? "rotate-180" : ""}`}>expand_more</span>
                            </div>
                          </button>
                          {isExpanded && (
                            <div className="mt-2 ml-2 flex flex-col gap-2 pl-4 border-l-2 border-outline-variant/10">
                              {entry.films_rated.map((f) => (
                                <Link key={f.movie_id} to={`/movies/${f.movie_id}`} className="flex items-center gap-3 group/film">
                                  <div className="w-8 h-12 rounded overflow-hidden bg-surface-container flex-shrink-0">
                                    {f.poster_path ? (
                                      <img src={`https://image.tmdb.org/t/p/w92${f.poster_path}`} alt={f.title} className="w-full h-full object-cover" />
                                    ) : (
                                      <div className="w-full h-full flex items-center justify-center"><span className="material-symbols-outlined text-xs text-outline">movie</span></div>
                                    )}
                                  </div>
                                  <span className="text-sm text-on-surface truncate group-hover/film:text-primary transition-colors">{f.title}</span>
                                  <span className="ml-auto text-xs font-bold text-primary-fixed-dim flex-shrink-0">{f.rating}/10</span>
                                </Link>
                              ))}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Dismissed Movies */}
        {dismissedTotal > 0 && (
          <section className="flex flex-col gap-6">
            <button
              onClick={() => setShowDismissed((v) => !v)}
              className="flex items-center gap-3 group"
            >
              <div>
                <h2 className="font-headline text-3xl font-black italic tracking-tighter text-on-surface mb-1 text-left">Not Interested</h2>
                <p className="text-on-surface-variant font-body text-left">
                  {dismissedTotal} movie{dismissedTotal !== 1 ? "s" : ""} you've dismissed from recommendations
                </p>
              </div>
              <span className={`material-symbols-outlined text-2xl text-on-surface-variant group-hover:text-primary transition-all ${showDismissed ? "rotate-180" : ""}`}>
                expand_more
              </span>
            </button>

            {showDismissed && (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
                {dismissedItems.map((item) => (
                  <div
                    key={item.movie_id}
                    className="relative group rounded-xl overflow-hidden bg-surface-container-low border border-outline-variant/10"
                  >
                    <Link to={`/movies/${item.movie_id}`} className="block">
                      <div className="aspect-[2/3] overflow-hidden">
                        {item.poster_path ? (
                          <img
                            src={`https://image.tmdb.org/t/p/w300${item.poster_path}`}
                            alt={item.movie_title ?? ""}
                            className="w-full h-full object-cover opacity-50 group-hover:opacity-75 transition-opacity duration-300"
                          />
                        ) : (
                          <div className="w-full h-full bg-surface-container flex items-center justify-center">
                            <span className="material-symbols-outlined text-4xl text-outline">movie</span>
                          </div>
                        )}
                      </div>
                    </Link>
                    <button
                      onClick={() => {
                        undismissMovie(userId, item.movie_id)
                          .then(() => {
                            setDismissedItems((prev) => prev.filter((d) => d.movie_id !== item.movie_id));
                            setDismissedTotal((prev) => prev - 1);
                          })
                          .catch(() => {});
                      }}
                      className="absolute top-2 right-2 bg-[#131314]/70 backdrop-blur-md p-1.5 rounded border border-white/10 hover:bg-error/60 transition-colors z-10"
                      title="Undo dismiss"
                    >
                      <span className="material-symbols-outlined text-[16px] text-error">undo</span>
                    </button>
                    <div className="p-3">
                      <p className="text-sm font-headline font-bold text-on-surface leading-tight truncate">
                        {item.movie_title ?? `Movie #${item.movie_id}`}
                      </p>
                      <p className="text-xs text-on-surface-variant mt-1">
                        {new Date(item.dismissed_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Rating History Table */}
        {user && ratings.length > 0 && (
          <section className="flex flex-col gap-6">
            <div className="flex justify-between items-end">
              <div>
                <h2 className="font-headline text-3xl font-black italic tracking-tighter text-on-surface mb-2">Rating History</h2>
                <p className="text-on-surface-variant font-body">Complete archive of theatrical reviews and scores.</p>
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setShowImportModal(true)}
                  className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold bg-primary/15 text-primary hover:bg-primary/25 transition-all"
                >
                  <span className="material-symbols-outlined text-base">upload_file</span>
                  Import
                </button>
                <button
                  onClick={handleExport}
                  disabled={exporting}
                  className="flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold bg-surface-container-low text-on-surface-variant hover:bg-surface-container transition-all disabled:opacity-40"
                >
                  <span className="material-symbols-outlined text-base">download</span>
                  {exporting ? "Exporting..." : "Export"}
                </button>
              </div>
            </div>
            <div className="overflow-hidden rounded-xl border border-outline-variant/10 bg-surface-container-lowest">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-high/50">
                    <th className="px-6 py-5 text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 border-b border-white/5">Movie</th>
                    <th className="px-6 py-5 text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 border-b border-white/5 text-center">Your Rating</th>
                    <th className="px-6 py-5 text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 border-b border-white/5 text-right">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {ratings.map((r) => (
                    <tr key={`${r.movie_id}-${r.timestamp}`} className="hover:bg-white/5 transition-colors group">
                      <td className="px-6 py-5 font-body text-sm text-on-surface-variant">
                        <a href={`/movies/${r.movie_id}`} className="text-primary hover:underline transition-colors">
                          {r.movie_title ?? `Movie #${r.movie_id}`}
                        </a>
                      </td>
                      <td className="px-6 py-5 text-center">{stars(r.rating)}</td>
                      <td className="px-6 py-5 text-right font-body text-sm text-on-surface-variant">
                        {new Date(r.timestamp).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {/* Pagination */}
              <div className="px-6 py-6 flex items-center justify-between border-t border-white/5 bg-surface-container/30">
                <span className="text-sm text-on-surface-variant font-body">
                  Showing <span className="text-on-surface font-medium">{offset + 1}-{Math.min(offset + limit, total)}</span> of{" "}
                  <span className="text-on-surface font-medium">{total}</span> ratings
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => changePage(Math.max(0, offset - limit))}
                    disabled={offset === 0}
                    className="flex items-center gap-1 px-4 py-2 text-xs font-bold uppercase tracking-widest text-on-surface-variant hover:text-primary transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    <span className="material-symbols-outlined text-sm">chevron_left</span> Previous
                  </button>
                  <div className="flex items-center gap-1">
                    {Array.from({ length: Math.min(totalPages, 5) }).map((_, i) => (
                      <button
                        key={i}
                        onClick={() => changePage(i * limit)}
                        className={`w-8 h-8 flex items-center justify-center rounded text-xs transition-colors ${
                          currentPage === i + 1
                            ? "bg-primary text-on-primary font-bold"
                            : "hover:bg-white/5 text-on-surface-variant"
                        }`}
                      >
                        {i + 1}
                      </button>
                    ))}
                    {totalPages > 5 && <span className="px-1 text-on-surface-variant">...</span>}
                  </div>
                  <button
                    onClick={() => changePage(offset + limit)}
                    disabled={offset + limit >= total}
                    className="flex items-center gap-1 px-4 py-2 text-xs font-bold uppercase tracking-widest text-on-surface-variant hover:text-primary transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Next <span className="material-symbols-outlined text-sm">chevron_right</span>
                  </button>
                </div>
              </div>
            </div>
          </section>
        )}
      </div>

      {/* Footer */}
      <footer className="mt-20 border-t border-white/5 bg-surface-container-lowest py-12 px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
          <div className="text-primary font-headline font-black italic text-xl tracking-tighter">CINEMA PRIVATE</div>
          <div className="flex gap-8 text-xs font-bold uppercase tracking-widest text-on-surface-variant">
            <a className="hover:text-primary transition-colors" href="http://localhost:8000/docs" target="_blank" rel="noopener noreferrer">API Docs</a>
            <a className="hover:text-primary transition-colors" href="http://localhost:8000/health" target="_blank" rel="noopener noreferrer">System Status</a>
          </div>
          <div className="text-xs text-on-surface-variant/50 font-body">
            &copy; 2024 CineMatch-AI. All rights reserved.
          </div>
        </div>
      </footer>

      <ImportRatingsModal
        isOpen={showImportModal}
        onClose={() => setShowImportModal(false)}
        userId={userId}
        onSuccess={handleImportSuccess}
      />
    </>
  );
}
