import { useEffect, useState } from "react";
import {
  getThematicCollections,
  getThematicCollectionDetail,
} from "../api/movies";
import type {
  ThematicCollectionSummary,
  ThematicCollectionMovieResult,
} from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import AddToListModal from "../components/AddToListModal";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useDismissed } from "../hooks/useDismissed";
import { useMatchPredictions } from "../hooks/useMatchPredictions";
import { useRated } from "../hooks/useRated";
import { useWatchlist } from "../hooks/useWatchlist";

const TYPE_TABS: { label: string; value: string | null }[] = [
  { label: "All", value: null },
  { label: "Genre & Decade", value: "genre_decade" },
  { label: "Director", value: "director" },
  { label: "Year", value: "year" },
];

const TYPE_ICONS: Record<string, string> = {
  genre_decade: "movie_filter",
  director: "person",
  year: "calendar_month",
};

export default function Curated() {
  const [collections, setCollections] = useState<ThematicCollectionSummary[]>(
    []
  );
  const [typeFilter, setTypeFilter] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [selectedTitle, setSelectedTitle] = useState("");
  const [selectedType, setSelectedType] = useState("");
  const [results, setResults] = useState<ThematicCollectionMovieResult[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } =
    useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const { getMatchPercent, fetchMatchPercents } = useMatchPredictions();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  // Load collection catalog
  useEffect(() => {
    if (selectedId !== null) return;
    setLoading(true);
    setError("");
    getThematicCollections(typeFilter ?? undefined)
      .then((data) => setCollections(data.results))
      .catch((e) => setError(e.detail || e.message || "Failed to load"))
      .finally(() => setLoading(false));
  }, [typeFilter, selectedId]);

  // Load collection detail
  useEffect(() => {
    if (selectedId === null) return;
    setLoading(true);
    setError("");
    getThematicCollectionDetail(selectedId, 40)
      .then((data) => {
        setResults(data.results);
        setTotal(data.total);
        setSelectedTitle(data.title);
        setSelectedType(data.collection_type);
        const ids = data.results.map((r) => r.movie.id);
        if (ids.length > 0) {
          refreshForMovieIds(ids);
          refreshDismissedForMovieIds(ids);
          refreshRatingsForMovieIds(ids);
          fetchMatchPercents(ids);
        }
      })
      .catch((e) => setError(e.detail || e.message || "Failed to load"))
      .finally(() => setLoading(false));
  }, [selectedId]);

  const handleSelect = (c: ThematicCollectionSummary) => {
    setSelectedId(c.id);
    setSelectedTitle(c.title);
    setSelectedType(c.collection_type);
  };

  const handleBack = () => {
    setSelectedId(null);
    setResults([]);
    setError("");
  };

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          {selectedId === null ? (
            <>
              {/* Catalog view */}
              <header className="mb-10">
                <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
                  Curated Collections
                </h1>
                <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
                  Auto-generated thematic lists to explore
                </p>
              </header>

              {/* Type filter tabs */}
              <div className="mb-10">
                <div className="flex gap-2 flex-wrap">
                  {TYPE_TABS.map((tab) => (
                    <button
                      key={tab.label}
                      onClick={() => setTypeFilter(tab.value)}
                      className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                        typeFilter === tab.value
                          ? "bg-primary-container text-on-primary-container shadow-md"
                          : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              </div>

              {loading && (
                <LoadingSpinner text="Loading collections..." />
              )}
              {error && (
                <ErrorPanel
                  message={error}
                  onRetry={() => window.location.reload()}
                />
              )}

              {!loading && !error && collections.length === 0 && (
                <p className="text-center text-on-surface-variant text-lg py-20">
                  No collections found.
                </p>
              )}

              {!loading && !error && collections.length > 0 && (
                <>
                  <p className="text-on-surface-variant text-sm mb-6">
                    <span className="font-bold text-on-surface">
                      {collections.length}
                    </span>{" "}
                    collection{collections.length !== 1 ? "s" : ""} available
                  </p>

                  <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {collections.map((c) => (
                      <button
                        key={c.id}
                        onClick={() => handleSelect(c)}
                        className="glass-card rounded-2xl p-5 text-left hover:bg-surface-container-high transition-all hover:scale-[1.03] duration-200 group"
                      >
                        {/* Preview posters */}
                        {c.preview_posters.length > 0 ? (
                          <div className="grid grid-cols-2 gap-1 mb-4 rounded-lg overflow-hidden aspect-square">
                            {c.preview_posters.slice(0, 4).map((p, i) => (
                              <img
                                key={i}
                                src={`https://image.tmdb.org/t/p/w200${p}`}
                                alt=""
                                className="w-full h-full object-cover"
                              />
                            ))}
                            {/* Fill empty slots */}
                            {Array.from({
                              length: Math.max(
                                0,
                                4 - c.preview_posters.length
                              ),
                            }).map((_, i) => (
                              <div
                                key={`empty-${i}`}
                                className="w-full h-full bg-surface-container-highest"
                              />
                            ))}
                          </div>
                        ) : (
                          <div className="flex items-center justify-center rounded-lg bg-surface-container-highest aspect-square mb-4">
                            <span className="material-symbols-outlined text-5xl text-on-surface-variant/30">
                              {TYPE_ICONS[c.collection_type] ||
                                "auto_awesome_mosaic"}
                            </span>
                          </div>
                        )}

                        <h2 className="font-headline font-bold text-on-surface text-sm md:text-base group-hover:text-[#FFC107] transition-colors line-clamp-2">
                          {c.title}
                        </h2>

                        <div className="mt-2 flex items-center gap-2 flex-wrap">
                          <span className="glass-card rounded-md px-2 py-1 text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
                            <span className="material-symbols-outlined text-xs align-middle mr-0.5">
                              {TYPE_ICONS[c.collection_type] ||
                                "auto_awesome_mosaic"}
                            </span>
                            {c.collection_type.replace("_", " ")}
                          </span>
                          <span className="text-on-surface-variant text-xs font-medium">
                            {c.movie_count} movie
                            {c.movie_count !== 1 ? "s" : ""}
                          </span>
                        </div>
                      </button>
                    ))}
                  </section>
                </>
              )}
            </>
          ) : (
            <>
              {/* Collection detail view */}
              <header className="mb-10">
                <button
                  onClick={handleBack}
                  className="flex items-center gap-1 text-on-surface-variant hover:text-on-surface text-sm font-medium mb-4 transition-colors"
                >
                  <span className="material-symbols-outlined text-lg">
                    arrow_back
                  </span>
                  All Collections
                </button>
                <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
                  {selectedTitle}
                </h1>
                <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
                  <span className="material-symbols-outlined text-sm align-middle mr-1">
                    {TYPE_ICONS[selectedType] || "auto_awesome_mosaic"}
                  </span>
                  {selectedType.replace("_", " ")} collection
                </p>
              </header>

              {loading && (
                <LoadingSpinner text="Loading collection..." />
              )}
              {error && (
                <ErrorPanel
                  message={error}
                  onRetry={() =>
                    selectedId && setSelectedId(selectedId)
                  }
                />
              )}

              {!loading && !error && results.length > 0 && (
                <>
                  <p className="text-on-surface-variant text-sm mb-6">
                    <span className="font-bold text-on-surface">{total}</span>{" "}
                    movie{total !== 1 ? "s" : ""}
                  </p>
                  <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
                    {results.map((item, index) => (
                      <div key={item.movie.id} className="relative">
                        <div className="absolute -top-2 -left-2 z-10 bg-[#FFC107] text-[#131314] w-8 h-8 rounded-full flex items-center justify-center text-xs font-black shadow-lg">
                          {index + 1}
                        </div>
                        <MovieCard
                          movie={item.movie}
                          isBookmarked={isInWatchlist(item.movie.id)}
                          onToggleBookmark={toggle}
                          onAddToList={(id) => setAddToListMovieId(id)}
                          isDismissed={isDismissed(item.movie.id)}
                          onDismiss={toggleDismiss}
                          userRating={getRating(item.movie.id)}
                          matchPercent={getMatchPercent(item.movie.id)}
                        />
                        <div className="mt-2 flex items-center gap-3 text-xs text-on-surface-variant font-medium">
                          <span>
                            <span
                              className="material-symbols-outlined text-sm align-middle mr-1"
                              style={{
                                fontVariationSettings: "'FILL' 1",
                              }}
                            >
                              star
                            </span>
                            {item.avg_rating.toFixed(1)} avg
                          </span>
                          <span>
                            <span className="material-symbols-outlined text-sm align-middle mr-1">
                              bar_chart
                            </span>
                            {item.rating_count.toLocaleString()} rating
                            {item.rating_count !== 1 ? "s" : ""}
                          </span>
                        </div>
                      </div>
                    ))}
                  </section>
                </>
              )}

              {!loading && !error && results.length === 0 && (
                <p className="text-center text-on-surface-variant text-lg py-20">
                  No movies found in this collection.{" "}
                  <button
                    onClick={handleBack}
                    className="text-[#FFC107] underline"
                  >
                    Browse other collections
                  </button>
                  .
                </p>
              )}
            </>
          )}
        </div>
      </main>
      <AddToListModal
        movieId={addToListMovieId}
        onClose={() => setAddToListMovieId(null)}
      />
      <BottomNav />
    </>
  );
}
