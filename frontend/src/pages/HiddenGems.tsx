import { useEffect, useState } from "react";
import { getGenres, getHiddenGems } from "../api/movies";
import type { HiddenGemResult } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import MovieCard from "../components/MovieCard";
import AddToListModal from "../components/AddToListModal";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useDismissed } from "../hooks/useDismissed";
import { useRated } from "../hooks/useRated";
import { useMatchPredictions } from "../hooks/useMatchPredictions";
import { useWatchlist } from "../hooks/useWatchlist";

const RATING_OPTIONS = [
  { value: 7.0, label: "7+" },
  { value: 7.5, label: "7.5+" },
  { value: 8.0, label: "8+" },
  { value: 8.5, label: "8.5+" },
];

const VOTES_OPTIONS = [
  { value: 50, label: "< 50 votes" },
  { value: 100, label: "< 100 votes" },
  { value: 250, label: "< 250 votes" },
  { value: 500, label: "< 500 votes" },
];

export default function HiddenGems() {
  const [minRating, setMinRating] = useState(7.5);
  const [maxVotes, setMaxVotes] = useState(100);
  const [genre, setGenre] = useState<string | null>(null);
  const [genres, setGenres] = useState<string[]>([]);
  const [results, setResults] = useState<HiddenGemResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const { getMatchPercent, fetchMatchPercents } = useMatchPredictions();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  useEffect(() => {
    getGenres()
      .then((data) => setGenres(data.genres.map((g) => g.genre)))
      .catch(() => {});
  }, []);

  const fetchGems = () => {
    setLoading(true);
    setError("");
    getHiddenGems({
      min_rating: minRating,
      max_votes: maxVotes,
      genre: genre ?? undefined,
      limit: 40,
    })
      .then((data) => {
        setResults(data.results);
        { const _ids = data.results.map((r) => r.movie.id); refreshForMovieIds(_ids); refreshDismissedForMovieIds(_ids); refreshRatingsForMovieIds(_ids); fetchMatchPercents(_ids); }
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchGems();
  }, [minRating, maxVotes, genre]);

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <header className="mb-10">
            <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
              Hidden Gems
            </h1>
            <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
              High-quality movies most users haven't discovered yet
            </p>
          </header>

          {/* Filters */}
          <div className="space-y-6 mb-10">
            {/* Min Rating */}
            <div>
              <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 block">
                Minimum Rating
              </span>
              <div className="flex gap-2">
                {RATING_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setMinRating(opt.value)}
                    className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                      minRating === opt.value
                        ? "bg-primary-container text-on-primary-container shadow-md"
                        : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Max Votes */}
            <div>
              <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 block">
                Popularity Cap
              </span>
              <div className="flex gap-2">
                {VOTES_OPTIONS.map((opt) => (
                  <button
                    key={opt.value}
                    onClick={() => setMaxVotes(opt.value)}
                    className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                      maxVotes === opt.value
                        ? "bg-primary-container text-on-primary-container shadow-md"
                        : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Genre Filter */}
            {genres.length > 0 && (
              <div>
                <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 block">
                  Genre
                </span>
                <div className="flex gap-2 flex-wrap">
                  <button
                    onClick={() => setGenre(null)}
                    className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                      genre === null
                        ? "bg-primary-container text-on-primary-container shadow-md"
                        : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                    }`}
                  >
                    All
                  </button>
                  {genres.map((g) => (
                    <button
                      key={g}
                      onClick={() => setGenre(g)}
                      className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                        genre === g
                          ? "bg-primary-container text-on-primary-container shadow-md"
                          : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                      }`}
                    >
                      {g}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {loading && <LoadingSpinner text="Uncovering hidden gems..." />}
          {error && <ErrorPanel message={error} onRetry={fetchGems} />}

          {!loading && !error && (
            <>
              <p className="text-on-surface-variant text-sm mb-6">
                <span className="font-bold text-on-surface">{results.length}</span> hidden gem{results.length !== 1 ? "s" : ""} found
              </p>
              <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
                {results.map((item) => (
                  <div key={item.movie.id} className="relative">
                    <div className="absolute -top-2 -left-2 z-10 bg-gradient-to-br from-[#FFC107] to-[#FF8F00] text-[#131314] px-2.5 py-1 rounded-full flex items-center gap-1 text-xs font-black shadow-lg">
                      <span className="material-symbols-outlined text-sm">diamond</span>
                      {item.vote_average.toFixed(1)}
                    </div>
                    <MovieCard
                      movie={item.movie}
                      isBookmarked={isInWatchlist(item.movie.id)}
                      onToggleBookmark={toggle} onAddToList={(id) => setAddToListMovieId(id)} isDismissed={isDismissed(item.movie.id)} onDismiss={toggleDismiss}
                      userRating={getRating(item.movie.id)}
                      matchPercent={getMatchPercent(item.movie.id)}
                    />
                    <p className="mt-2 text-xs text-on-surface-variant font-medium">
                      <span className="material-symbols-outlined text-sm align-middle mr-1">visibility</span>
                      {item.vote_count.toLocaleString()} vote{item.vote_count !== 1 ? "s" : ""}
                    </p>
                  </div>
                ))}
              </section>
            </>
          )}

          {!loading && !error && results.length === 0 && (
            <p className="text-center text-on-surface-variant text-lg py-20">
              No hidden gems found with these filters. Try lowering the rating or raising the vote cap.
            </p>
          )}
        </div>
      </main>
      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
      <BottomNav />
    </>
  );
}
