import { useEffect, useState } from "react";
import { getCompletions, getDirectorGaps, getActorGaps } from "../../api/users";
import type { CollectionGroup } from "../../api/types";
import ErrorPanel from "../../components/ErrorPanel";
import LoadingSpinner from "../../components/LoadingSpinner";
import MovieCard from "../../components/MovieCard";
import AddToListModal from "../../components/AddToListModal";
import { useUserId } from "../../hooks/useUserId";
import { useDismissed } from "../../hooks/useDismissed";
import { useMatchPredictions } from "../../hooks/useMatchPredictions";
import { useRated } from "../../hooks/useRated";
import { useWatchlist } from "../../hooks/useWatchlist";

type Source = "completion" | "director-gap" | "actor-gap";
type ViewFilter = "all" | "in-progress" | "discover";
type CreatorFilter = "both" | "directors" | "actors";

interface TaggedGroup extends CollectionGroup {
  source: Source;
}

const VIEW_OPTIONS: { value: ViewFilter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "in-progress", label: "In Progress" },
  { value: "discover", label: "Discover More" },
];

const CREATOR_OPTIONS: { value: CreatorFilter; label: string }[] = [
  { value: "both", label: "Both" },
  { value: "directors", label: "Directors" },
  { value: "actors", label: "Actors" },
];

export default function CollectionsTab() {
  const { userId } = useUserId();
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const { getMatchPercent, fetchMatchPercents } = useMatchPredictions();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  const [allGroups, setAllGroups] = useState<TaggedGroup[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [viewFilter, setViewFilter] = useState<ViewFilter>("all");
  const [creatorFilter, setCreatorFilter] = useState<CreatorFilter>("both");

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    setError("");
    Promise.all([
      getCompletions(userId, 20),
      getDirectorGaps(userId, 20),
      getActorGaps(userId, 20),
    ])
      .then(([compData, dirData, actData]) => {
        const tagged: TaggedGroup[] = [
          ...compData.groups.map((g) => ({ ...g, source: "completion" as Source })),
          ...dirData.groups.map((g) => ({ ...g, source: "director-gap" as Source })),
          ...actData.groups.map((g) => ({ ...g, source: "actor-gap" as Source })),
        ];
        // Sort by progress percentage descending
        tagged.sort((a, b) => {
          const pctA = a.rated_count / a.total_by_creator;
          const pctB = b.rated_count / b.total_by_creator;
          return pctB - pctA;
        });
        setAllGroups(tagged);
        const allMovieIds = tagged.flatMap((g) => g.missing.map((m) => m.id));
        if (allMovieIds.length > 0) {
          refreshForMovieIds(allMovieIds);
          refreshDismissedForMovieIds(allMovieIds);
          refreshRatingsForMovieIds(allMovieIds);
          fetchMatchPercents(allMovieIds);
        }
      })
      .catch((e) => setError(e.detail || e.message || "Failed to load"))
      .finally(() => setLoading(false));
  }, [userId]);

  const filtered = allGroups.filter((g) => {
    // View filter
    if (viewFilter === "in-progress" && g.source !== "completion") return false;
    if (viewFilter === "discover" && g.source === "completion") return false;
    // Creator filter
    if (creatorFilter === "directors" && g.creator_type !== "director") return false;
    if (creatorFilter === "actors" && g.creator_type !== "actor") return false;
    return true;
  });

  const filteredMissing = filtered.reduce((sum, g) => sum + g.missing.length, 0);

  function renderGroup(group: TaggedGroup) {
    const pct = Math.round(
      (group.rated_count / group.total_by_creator) * 100
    );
    return (
      <section key={`${group.source}-${group.creator_type}-${group.creator_name}`}>
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
            <div className="flex items-center gap-2">
              <p className="text-on-surface-variant text-xs font-bold uppercase tracking-widest">
                {group.creator_type}
              </p>
              {viewFilter === "all" && (
                <span className={`text-[10px] font-bold uppercase tracking-widest px-1.5 py-0.5 rounded ${
                  group.source === "completion"
                    ? "bg-[#FFC107]/10 text-[#FFC107]"
                    : "bg-primary/10 text-primary"
                }`}>
                  {group.source === "completion" ? "In Progress" : "Discover"}
                </span>
              )}
            </div>
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
              {group.missing.length} to discover
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
              matchPercent={getMatchPercent(movie.id)}
            />
          ))}
        </div>
      </section>
    );
  }

  return (
    <>
      <header className="mb-10">
        <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
          Collections
        </h1>
        <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
          Films by creators you love
        </p>
      </header>

      {/* Filter bar */}
      {!loading && !error && allGroups.length > 0 && (
        <div className="flex flex-wrap items-center gap-4 mb-8">
          {/* View filter */}
          <div className="flex rounded-xl bg-surface-container-highest/50 p-1">
            {VIEW_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setViewFilter(opt.value)}
                className={`px-4 py-2 rounded-lg text-xs font-bold uppercase tracking-widest transition-all ${
                  viewFilter === opt.value
                    ? "bg-[#FFC107] text-on-surface shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>

          {/* Creator sub-filter */}
          <div className="flex rounded-xl bg-surface-container-highest/50 p-1">
            {CREATOR_OPTIONS.map((opt) => (
              <button
                key={opt.value}
                onClick={() => setCreatorFilter(opt.value)}
                className={`px-3 py-2 rounded-lg text-xs font-bold uppercase tracking-widest transition-all ${
                  creatorFilter === opt.value
                    ? "bg-[#FFC107] text-on-surface shadow-sm"
                    : "text-on-surface-variant hover:text-on-surface"
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {loading && <LoadingSpinner text="Finding your collections..." />}
      {error && (
        <ErrorPanel
          message={error}
          onRetry={() => window.location.reload()}
        />
      )}

      {!loading && !error && allGroups.length === 0 && (
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

      {!loading && !error && allGroups.length > 0 && (
        <>
          {filtered.length === 0 ? (
            <div className="text-center py-20">
              <span className="material-symbols-outlined text-5xl text-on-surface-variant mb-4 block">
                filter_list_off
              </span>
              <p className="text-on-surface-variant text-lg max-w-md mx-auto">
                No collections match the current filters. Try adjusting your selection.
              </p>
            </div>
          ) : (
            <>
              <p className="text-on-surface-variant text-sm mb-8">
                {filteredMissing} film{filteredMissing !== 1 ? "s" : ""} to discover
                across {filtered.length} collection
                {filtered.length !== 1 ? "s" : ""}
              </p>

              <div className="space-y-12">
                {filtered.map(renderGroup)}
              </div>
            </>
          )}
        </>
      )}

      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
    </>
  );
}
