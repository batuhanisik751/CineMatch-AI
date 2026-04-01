import { useEffect, useState } from "react";
import { getCompletions } from "../api/users";
import type { CollectionGroup } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import AddToListModal from "../components/AddToListModal";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";
import { useDismissed } from "../hooks/useDismissed";
import { useRated } from "../hooks/useRated";
import { useWatchlist } from "../hooks/useWatchlist";

export default function Collections() {
  const { userId } = useUserId();
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  const [groups, setGroups] = useState<CollectionGroup[]>([]);
  const [totalMissing, setTotalMissing] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    setError("");
    getCompletions(userId, 20)
      .then((data) => {
        setGroups(data.groups);
        setTotalMissing(data.total_missing);
        const allMovieIds = data.groups.flatMap((g) =>
          g.missing.map((m) => m.id)
        );
        if (allMovieIds.length > 0) { refreshForMovieIds(allMovieIds); refreshDismissedForMovieIds(allMovieIds); refreshRatingsForMovieIds(allMovieIds); }
      })
      .catch((e) => setError(e.detail || e.message || "Failed to load"))
      .finally(() => setLoading(false));
  }, [userId]);

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <header className="mb-10">
            <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
              Complete the Collection
            </h1>
            <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
              Films you haven't seen yet by creators you love
            </p>
          </header>

          {loading && <LoadingSpinner text="Finding your collections..." />}
          {error && (
            <ErrorPanel
              message={error}
              onRetry={() => window.location.reload()}
            />
          )}

          {!loading && !error && groups.length === 0 && (
            <div className="text-center py-20">
              <span className="material-symbols-outlined text-5xl text-on-surface-variant mb-4 block">
                collections_bookmark
              </span>
              <p className="text-on-surface-variant text-lg max-w-md mx-auto">
                You haven't rated enough films by any single director or actor
                yet. Rate at least 3 films by the same creator to see
                suggestions here.
              </p>
            </div>
          )}

          {!loading && !error && groups.length > 0 && (
            <>
              <p className="text-on-surface-variant text-sm mb-8">
                {totalMissing} film{totalMissing !== 1 ? "s" : ""} to discover
                across {groups.length} collection
                {groups.length !== 1 ? "s" : ""}
              </p>

              <div className="space-y-12">
                {groups.map((group) => {
                  const pct = Math.round(
                    (group.rated_count / group.total_by_creator) * 100
                  );
                  return (
                    <section key={`${group.creator_type}-${group.creator_name}`}>
                      {/* Group header */}
                      <div className="flex items-center gap-3 mb-2">
                        <div className="w-10 h-10 rounded-full bg-[#FFC107]/10 flex items-center justify-center">
                          <span className="material-symbols-outlined text-[#FFC107] text-xl">
                            {group.creator_type === "director"
                              ? "movie_filter"
                              : "theater_comedy"}
                          </span>
                        </div>
                        <div>
                          <h2 className="font-headline font-bold text-on-surface text-lg md:text-xl">
                            {group.creator_name}
                          </h2>
                          <p className="text-on-surface-variant text-xs font-bold uppercase tracking-widest">
                            {group.creator_type}
                          </p>
                        </div>
                      </div>

                      {/* Stats row */}
                      <div className="flex flex-wrap items-center gap-3 mb-4">
                        <span className="glass-card rounded-lg px-3 py-1.5 text-xs font-bold text-[#FFC107]">
                          <span className="material-symbols-outlined text-sm align-middle mr-1">
                            person
                          </span>
                          {group.rated_count} of {group.total_by_creator} rated
                        </span>
                        <span className="glass-card rounded-lg px-3 py-1.5 text-xs font-bold text-on-surface-variant">
                          <span
                            className="material-symbols-outlined text-sm align-middle mr-1"
                            style={{ fontVariationSettings: "'FILL' 1" }}
                          >
                            star
                          </span>
                          Your avg: {group.avg_rating.toFixed(1)}/10
                        </span>
                      </div>

                      {/* Progress bar */}
                      <div className="mb-6 max-w-md">
                        <div className="flex justify-between text-xs text-on-surface-variant mb-1">
                          <span>{pct}% complete</span>
                          <span>
                            {group.missing.length} remaining
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-surface-container-highest overflow-hidden">
                          <div
                            className="h-full rounded-full bg-[#FFC107] transition-all duration-500"
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      </div>

                      {/* Movie grid */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
                        {group.missing.map((movie) => (
                          <MovieCard
                            key={movie.id}
                            movie={movie}
                            isBookmarked={isInWatchlist(movie.id)}
                            onToggleBookmark={toggle}
                            onAddToList={(id) => setAddToListMovieId(id)}
                            isDismissed={isDismissed(movie.id)}
                            onDismiss={toggleDismiss}
                            userRating={getRating(movie.id)}
                          />
                        ))}
                      </div>
                    </section>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </main>
      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
      <BottomNav />
    </>
  );
}
