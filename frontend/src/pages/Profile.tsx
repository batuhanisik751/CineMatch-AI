import { useEffect, useState } from "react";
import { getUserRatings } from "../api/ratings";
import type { RatingResponse, UserResponse } from "../api/types";
import { getUser } from "../api/users";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";

export default function Profile() {
  const { userId } = useUserId();
  const [user, setUser] = useState<UserResponse | null>(null);
  const [ratings, setRatings] = useState<RatingResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const limit = 20;

  const fetchUser = async () => {
    setLoading(true);
    setError("");
    try {
      const [u, r] = await Promise.all([
        getUser(userId),
        getUserRatings(userId, 0, limit),
      ]);
      setUser(u);
      setRatings(r.ratings);
      setTotal(r.total);
      setOffset(0);
    } catch {
      // User hasn't rated anything yet — that's fine, not an error
      setUser(null);
      setRatings([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userId]);

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
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.5;
    const empty = 5 - full - (half ? 1 : 0);
    return (
      <div className="flex items-center justify-center gap-0.5 text-primary-fixed-dim">
        {Array.from({ length: full }).map((_, i) => (
          <span key={`f${i}`} className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
        ))}
        {half && <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>star_half</span>}
        {Array.from({ length: empty }).map((_, i) => (
          <span key={`e${i}`} className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 0" }}>star</span>
        ))}
      </div>
    );
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <>
      <TopNav />
      <main className="pt-32 pb-20 px-8 max-w-7xl mx-auto flex flex-col gap-12">
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
                <span className="font-headline text-2xl font-bold text-on-surface">{total}</span>
              </div>
              <div className="p-6 rounded-xl bg-surface-container-low flex flex-col gap-2">
                <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/50">Avg Rating</span>
                <span className="font-headline text-2xl font-bold text-on-surface">
                  {ratings.length > 0 ? (ratings.reduce((sum, r) => sum + r.rating, 0) / ratings.length).toFixed(1) : "—"}
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
              <div className="text-center space-y-3">
                <span className="material-symbols-outlined text-5xl text-outline/40">movie_filter</span>
                <p className="text-on-surface-variant">You haven't rated any movies yet. Browse and rate movies to build your profile!</p>
              </div>
            </div>
          )}
        </section>

        {loading && <div className="flex justify-center py-12"><div className="w-12 h-12 border-4 border-primary-container/20 border-t-primary-container rounded-full animate-spin" /></div>}
        {error && <ErrorPanel message={error} />}

        {/* Rating History Table */}
        {user && ratings.length > 0 && (
          <section className="flex flex-col gap-6">
            <div className="flex justify-between items-end">
              <div>
                <h2 className="font-headline text-3xl font-black italic tracking-tighter text-on-surface mb-2">Rating History</h2>
                <p className="text-on-surface-variant font-body">Complete archive of theatrical reviews and scores.</p>
              </div>
            </div>
            <div className="overflow-hidden rounded-xl border border-outline-variant/10 bg-surface-container-lowest">
              <table className="w-full text-left border-collapse">
                <thead>
                  <tr className="bg-surface-container-high/50">
                    <th className="px-6 py-5 text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 border-b border-white/5">Movie ID</th>
                    <th className="px-6 py-5 text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 border-b border-white/5 text-center">Your Rating</th>
                    <th className="px-6 py-5 text-xs font-bold uppercase tracking-widest text-on-surface-variant/70 border-b border-white/5 text-right">Timestamp</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {ratings.map((r) => (
                    <tr key={`${r.movie_id}-${r.timestamp}`} className="hover:bg-white/5 transition-colors group">
                      <td className="px-6 py-5 font-body text-sm text-on-surface-variant">#{r.movie_id}</td>
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

        {/* Bento Stats */}
        {user && ratings.length > 0 && (
          <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
              <span className="material-symbols-outlined text-primary mb-4 text-3xl">movie_filter</span>
              <div className="text-4xl font-headline font-black text-on-surface mb-1">{total}</div>
              <div className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/60">Movies Reviewed</div>
            </div>
            <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
              <span className="material-symbols-outlined text-primary mb-4 text-3xl">star_half</span>
              <div className="text-4xl font-headline font-black text-on-surface mb-1">
                {(ratings.reduce((sum, r) => sum + r.rating, 0) / ratings.length).toFixed(1)}
              </div>
              <div className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/60">Average Rating</div>
            </div>
            <div className="p-8 rounded-xl bg-surface-container-low border border-outline-variant/5">
              <span className="material-symbols-outlined text-primary mb-4 text-3xl">verified</span>
              <div className="text-4xl font-headline font-black text-on-surface mb-1">Active</div>
              <div className="text-xs font-bold uppercase tracking-widest text-on-surface-variant/60">CineMatch Status</div>
            </div>
          </section>
        )}
      </main>

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
      <BottomNav />
    </>
  );
}
