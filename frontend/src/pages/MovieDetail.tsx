import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Cell,
  ResponsiveContainer,
} from "recharts";
import { addMovieToList, getUserLists } from "../api/lists";
import { getMovie, getMovieRatingStats, getSimilarMovies } from "../api/movies";
import { addRating } from "../api/ratings";
import { languageName } from "../constants/languages";
import type { MovieRatingStatsResponse, MovieResponse, SimilarMovie, UserListSummary } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import Modal from "../components/Modal";
import StarRating from "../components/StarRating";
import TopNav from "../components/TopNav";
import { useRated } from "../hooks/useRated";
import { useUserId } from "../hooks/useUserId";
import { useWatchlist } from "../hooks/useWatchlist";
import MovieConnections from "../components/MovieConnections";
import MovieDNA from "../components/MovieDNA";
import PopularityTimeline from "../components/PopularityTimeline";

function posterUrl(path: string | null, size = "w500") {
  return path ? `https://image.tmdb.org/t/p/${size}${path}` : null;
}

export default function MovieDetail() {
  const { id } = useParams<{ id: string }>();
  const [movie, setMovie] = useState<MovieResponse | null>(null);
  const [similar, setSimilar] = useState<SimilarMovie[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const { userId } = useUserId();
  const [userRating, setUserRating] = useState(0);
  const [ratingMsg, setRatingMsg] = useState("");
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { setLocalRating } = useRated();
  const [ratingStats, setRatingStats] = useState<MovieRatingStatsResponse | null>(null);
  const [statsLoading, setStatsLoading] = useState(false);
  const [statsRefresh, setStatsRefresh] = useState(0);

  // Add to List state
  const [showListModal, setShowListModal] = useState(false);
  const [userLists, setUserLists] = useState<UserListSummary[]>([]);
  const [listsLoading, setListsLoading] = useState(false);
  const [addedToLists, setAddedToLists] = useState<Set<number>>(new Set());

  const openListModal = () => {
    setShowListModal(true);
    setListsLoading(true);
    getUserLists(userId)
      .then((resp) => setUserLists(resp.lists))
      .catch(() => setUserLists([]))
      .finally(() => setListsLoading(false));
  };

  const handleAddToList = async (listId: number) => {
    if (!movie) return;
    try {
      await addMovieToList(userId, listId, movie.id);
      setAddedToLists((prev) => new Set([...prev, listId]));
    } catch {
      // silent
    }
  };

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([getMovie(Number(id)), getSimilarMovies(Number(id), 10)])
      .then(([m, s]) => {
        setMovie(m);
        setSimilar(s.similar);
        refreshForMovieIds([m.id]);
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  }, [id]);

  useEffect(() => {
    if (!movie) return;
    setStatsLoading(true);
    getMovieRatingStats(movie.id, userId)
      .then(setRatingStats)
      .catch(() => setRatingStats(null))
      .finally(() => setStatsLoading(false));
  }, [movie?.id, userId, statsRefresh]);

  const handleRate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (userRating === 0 || !movie) return;
    try {
      await addRating(userId, movie.id, userRating);
      setLocalRating(movie.id, userRating);
      setRatingMsg("Rating submitted!");
      setStatsRefresh((c) => c + 1);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to submit";
      setRatingMsg(msg);
    }
  };

  if (loading) return <><TopNav /><LoadingSpinner text="Loading movie details..." /></>;
  if (error) return <><TopNav /><div className="pt-32 px-8"><ErrorPanel message={error} /></div></>;
  if (!movie) return null;

  const poster = posterUrl(movie.poster_path);
  const year = movie.release_date ? new Date(movie.release_date).getFullYear() : null;

  return (
    <>
      <TopNav />
      <main className="pt-20">
        {/* Hero Section */}
        <section className="relative h-[870px] w-full overflow-hidden">
          <div className="absolute inset-0 z-0">
            <div className="w-full h-full bg-surface-container-lowest" />
            <div className="absolute inset-0 bg-gradient-to-t from-background via-background/60 to-transparent" />
            <div className="absolute inset-0 bg-gradient-to-r from-background via-transparent to-transparent" />
          </div>
          <div className="relative z-10 max-w-7xl mx-auto px-8 h-full flex flex-col md:flex-row items-end pb-16 gap-12">
            {/* Poster */}
            {poster && (
              <div className="w-full md:w-80 shrink-0 transform -rotate-1 hidden md:block">
                <div className="glass-card p-2 rounded-xl shadow-2xl overflow-hidden">
                  <img src={poster} alt={movie.title} className="w-full aspect-[2/3] object-cover rounded-lg" />
                </div>
              </div>
            )}
            {/* Content */}
            <div className="flex-1 space-y-6">
              <div className="flex flex-wrap gap-3">
                {movie.genres.map((g) => (
                  <span key={g} className="bg-secondary-container/20 text-secondary border border-secondary/30 px-3 py-1 rounded-full text-xs font-semibold tracking-widest uppercase">
                    {g}
                  </span>
                ))}
              </div>
              <h1 className="text-6xl md:text-8xl font-extrabold font-headline tracking-tighter text-on-surface leading-none text-glow">
                {movie.title.toUpperCase()}
              </h1>
              <div className="flex items-center gap-6 text-on-surface-variant font-body">
                <div className="flex items-center gap-2">
                  <span className="material-symbols-outlined text-primary-fixed-dim" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                  <span className="text-on-surface font-bold text-lg">{movie.vote_average.toFixed(1)}</span>
                  <span className="text-xs opacity-60">({movie.vote_count.toLocaleString()} votes)</span>
                </div>
                {year && <><div className="w-px h-4 bg-outline-variant/30" /><span className="text-sm">{year}</span></>}
              </div>
              {movie.overview && (
                <p className="text-lg md:text-xl text-on-surface/80 max-w-2xl leading-relaxed font-body">
                  {movie.overview}
                </p>
              )}
            </div>
          </div>
        </section>

        {/* Details Grid */}
        <section className="max-w-7xl mx-auto px-8 py-16">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
            {/* Left: Details */}
            <div className="lg:col-span-8 space-y-16">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-8 pb-12 border-b border-outline-variant/10">
                <div>
                  <p className="text-on-surface-variant text-xs uppercase tracking-widest mb-1 font-label">Director</p>
                  <p className="text-on-surface font-bold">{movie.director || "Unknown"}</p>
                </div>
                <div>
                  <p className="text-on-surface-variant text-xs uppercase tracking-widest mb-1 font-label">Release Date</p>
                  <p className="text-on-surface font-bold">{movie.release_date || "N/A"}</p>
                </div>
                <div>
                  <p className="text-on-surface-variant text-xs uppercase tracking-widest mb-1 font-label">Popularity</p>
                  <p className="text-on-surface font-bold">{movie.popularity.toFixed(1)}</p>
                </div>
                <div>
                  <p className="text-on-surface-variant text-xs uppercase tracking-widest mb-1 font-label">Vote Count</p>
                  <p className="text-on-surface font-bold">{movie.vote_count.toLocaleString()}</p>
                </div>
                <div>
                  <p className="text-on-surface-variant text-xs uppercase tracking-widest mb-1 font-label">Language</p>
                  <p className="text-on-surface font-bold">{movie.original_language ? languageName(movie.original_language) : "N/A"}</p>
                </div>
                <div>
                  <p className="text-on-surface-variant text-xs uppercase tracking-widest mb-1 font-label">Runtime</p>
                  <p className="text-on-surface font-bold">
                    {movie.runtime
                      ? movie.runtime >= 60
                        ? `${Math.floor(movie.runtime / 60)}h ${movie.runtime % 60}m`
                        : `${movie.runtime}m`
                      : "N/A"}
                  </p>
                </div>
              </div>
              {/* Cast */}
              {movie.cast_names.length > 0 && (
                <div className="space-y-6">
                  <h3 className="text-2xl font-headline font-bold text-on-surface">Top Cast</h3>
                  <div className="flex flex-wrap gap-3">
                    {movie.cast_names.map((name) => (
                      <span key={name} className="bg-surface-container-low border border-outline-variant/20 px-4 py-2 text-sm text-on-surface rounded-lg">{name}</span>
                    ))}
                  </div>
                </div>
              )}
              {/* Keywords */}
              {movie.keywords.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-lg font-headline font-bold text-on-surface">Keywords</h3>
                  <div className="flex flex-wrap gap-2">
                    {movie.keywords.map((k) => (
                      <span key={k} className="bg-surface-container-low border border-outline-variant/20 px-3 py-1 text-xs text-on-surface-variant rounded">{k}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {/* Right: Rating + Meta */}
            <div className="lg:col-span-4 space-y-8">
              <div className="glass-card p-8 rounded-2xl flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-headline font-bold text-on-surface">Watchlist</h3>
                  <p className="text-sm text-on-surface-variant">
                    {isInWatchlist(movie.id) ? "In your watchlist" : "Save for later"}
                  </p>
                </div>
                <button
                  onClick={() => toggle(movie.id)}
                  className="p-2 rounded-lg hover:bg-surface-container transition-colors"
                >
                  <span
                    className="material-symbols-outlined text-3xl text-primary"
                    style={isInWatchlist(movie.id) ? { fontVariationSettings: "'FILL' 1" } : undefined}
                  >
                    bookmark
                  </span>
                </button>
              </div>
              {/* Add to List */}
              <div className="glass-card p-8 rounded-2xl flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-headline font-bold text-on-surface">Add to List</h3>
                  <p className="text-sm text-on-surface-variant">Save to a collection</p>
                </div>
                <button
                  onClick={openListModal}
                  className="p-2 rounded-lg hover:bg-surface-container transition-colors"
                >
                  <span className="material-symbols-outlined text-3xl text-primary">
                    playlist_add
                  </span>
                </button>
              </div>
              <div className="glass-card p-8 rounded-2xl space-y-6">
                <h3 className="text-xl font-headline font-bold text-on-surface">Rate this Movie</h3>
                <form onSubmit={handleRate} className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-on-surface-variant text-sm">Your Rating</span>
                    <span className="text-primary font-bold text-xl">{userRating ? `${userRating}/10` : "—"}</span>
                  </div>
                  <StarRating value={userRating} onChange={setUserRating} />
                  <button type="submit" className="w-full bg-primary-container/20 border border-primary-container/40 text-primary py-3 rounded-md font-bold hover:bg-primary-container hover:text-on-primary-container transition-all">
                    Submit Review
                  </button>
                  {ratingMsg && <p className="text-sm text-center text-primary">{ratingMsg}</p>}
                </form>
              </div>
              {/* Community Rating Stats */}
              {statsLoading && (
                <div className="glass-card p-8 rounded-2xl space-y-4">
                  <div className="h-5 w-40 bg-surface-container rounded animate-pulse" />
                  <div className="h-48 bg-surface-container rounded animate-pulse" />
                </div>
              )}
              {!statsLoading && ratingStats && ratingStats.total_ratings > 0 && (
                <div className="glass-card p-8 rounded-2xl space-y-6">
                  <h3 className="text-xl font-headline font-bold text-on-surface">Community Ratings</h3>
                  <div className="grid grid-cols-4 gap-4 text-center">
                    <div>
                      <p className="text-on-surface-variant text-xs uppercase tracking-widest mb-1 font-label">Avg</p>
                      <p className="text-on-surface font-bold text-lg">{ratingStats.avg_rating.toFixed(1)}</p>
                    </div>
                    <div>
                      <p className="text-on-surface-variant text-xs uppercase tracking-widest mb-1 font-label">Median</p>
                      <p className="text-on-surface font-bold text-lg">{ratingStats.median_rating.toFixed(1)}</p>
                    </div>
                    <div>
                      <p className="text-on-surface-variant text-xs uppercase tracking-widest mb-1 font-label">Total</p>
                      <p className="text-on-surface font-bold text-lg">{ratingStats.total_ratings.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-on-surface-variant text-xs uppercase tracking-widest mb-1 font-label">Spread</p>
                      <p className="text-on-surface font-bold text-lg">{ratingStats.stddev.toFixed(1)}</p>
                    </div>
                  </div>
                  {/* Polarization indicator */}
                  {(() => {
                    const p = ratingStats.polarization_score;
                    const label = p < 0.2 ? "Strong consensus" : p < 0.4 ? "Mostly agreed" : p < 0.6 ? "Mixed opinions" : p < 0.8 ? "Divisive" : "Highly polarizing";
                    const color = p < 0.2 ? "#4ade80" : p < 0.4 ? "#60a5fa" : p < 0.6 ? "#facc15" : p < 0.8 ? "#fb923c" : "#f87171";
                    return (
                      <div className="space-y-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-on-surface-variant font-label uppercase tracking-widest">Polarization</span>
                          <span className="font-bold" style={{ color }}>{label}</span>
                        </div>
                        <div className="w-full h-2 rounded-full bg-surface-container-highest overflow-hidden">
                          <div className="h-full rounded-full transition-all duration-500" style={{ width: `${Math.min(p * 100, 100)}%`, backgroundColor: color }} />
                        </div>
                      </div>
                    );
                  })()}
                  <ResponsiveContainer width="100%" height={180}>
                    <BarChart data={ratingStats.distribution} margin={{ top: 8, right: 4, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" vertical={false} />
                      <XAxis dataKey="rating" tick={{ fill: "#a8a29e", fontSize: 12 }} axisLine={false} tickLine={false} />
                      <YAxis tick={{ fill: "#a8a29e", fontSize: 11 }} axisLine={false} tickLine={false} />
                      <Tooltip
                        contentStyle={{ backgroundColor: "#1c1b1f", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 8 }}
                        labelStyle={{ color: "#e5e2e3" }}
                        itemStyle={{ color: "#d4c5ab" }}
                        formatter={(value) => [typeof value === "number" ? value.toLocaleString() : String(value ?? "0"), "Ratings"]}
                        labelFormatter={(label) => `Rating: ${label}/10`}
                      />
                      <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                        {ratingStats.distribution.map((entry) => (
                          <Cell
                            key={entry.rating}
                            fill={ratingStats.user_rating !== null && entry.rating === ratingStats.user_rating ? "#FFC107" : "#4a4458"}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  {ratingStats.user_rating !== null && (
                    <p className="text-center text-sm text-on-surface-variant">
                      <span className="inline-block w-3 h-3 rounded-sm mr-1.5 align-middle" style={{ backgroundColor: "#FFC107" }} />
                      Your rating: <span className="text-primary font-bold">{ratingStats.user_rating}/10</span>
                    </p>
                  )}
                </div>
              )}
              {/* Meta Links */}
              <div className="space-y-4 px-2">
                <div className="flex items-center justify-between text-sm py-3 border-b border-outline-variant/10">
                  <span className="text-on-surface-variant">TMDb ID</span>
                  <span className="text-primary font-mono">#{movie.tmdb_id}</span>
                </div>
                {movie.imdb_id && (
                  <div className="flex items-center justify-between text-sm py-3 border-b border-outline-variant/10">
                    <span className="text-on-surface-variant">IMDb ID</span>
                    <a href={`https://www.imdb.com/title/${movie.imdb_id}`} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline font-mono">{movie.imdb_id}</a>
                  </div>
                )}
              </div>
            </div>
          </div>
        </section>

        {/* Movie DNA */}
        {movie && (
          <section className="bg-surface-container-lowest py-10 overflow-hidden">
            <div className="max-w-7xl mx-auto px-8">
              <MovieDNA movieId={movie.id} />
            </div>
          </section>
        )}

        {/* Popularity Timeline */}
        {movie && (
          <section className="bg-surface-container-lowest py-10 overflow-hidden">
            <div className="max-w-7xl mx-auto px-8">
              <PopularityTimeline movieId={movie.id} />
            </div>
          </section>
        )}

        {/* Similar Movies */}
        {similar.length > 0 && (
          <section className="bg-surface-container-lowest py-20 overflow-hidden">
            <div className="max-w-7xl mx-auto px-8 mb-8 flex items-center justify-between">
              <h3 className="text-3xl font-headline font-extrabold text-on-surface tracking-tight">Similar Movies</h3>
              <Link
                to={`/recommendations/from-seed/${movie.id}`}
                className="flex items-center gap-2 bg-primary-container/20 border border-primary-container/40 text-primary px-4 py-2 rounded-lg font-bold text-sm hover:bg-primary-container hover:text-on-primary-container transition-all"
              >
                <span className="material-symbols-outlined text-lg">auto_awesome</span>
                More Like This
              </Link>
            </div>
            <div className="flex gap-6 overflow-x-auto px-8 pb-10 hide-scrollbar scroll-smooth">
              {similar.map((s) => {
                const p = posterUrl(s.movie.poster_path, "w300");
                return (
                  <Link to={`/movies/${s.movie.id}`} key={s.movie.id} className="w-64 shrink-0 group">
                    <div className="relative aspect-[2/3] rounded-xl overflow-hidden mb-4 shadow-lg">
                      {p ? (
                        <img src={p} alt={s.movie.title} className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500" />
                      ) : (
                        <div className="w-full h-full bg-surface-container flex items-center justify-center">
                          <span className="material-symbols-outlined text-4xl text-outline">movie</span>
                        </div>
                      )}
                      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end p-4">
                        <span className="w-full py-2 bg-primary-container text-on-primary-container rounded font-bold text-sm text-center block">
                          {(s.similarity * 100).toFixed(0)}% Match
                        </span>
                      </div>
                    </div>
                    <h4 className="text-on-surface font-bold truncate">{s.movie.title}</h4>
                    <p className="text-on-surface-variant text-sm">{s.movie.genres.slice(0, 2).join(" · ")}</p>
                  </Link>
                );
              })}
            </div>
          </section>
        )}

        {/* Six Degrees — Movie Connections */}
        {movie && <MovieConnections currentMovieId={movie.id} />}
      </main>
      <BottomNav />

      {/* Add to List modal */}
      <Modal isOpen={showListModal} title="Add to List" onClose={() => setShowListModal(false)}>
        <div className="space-y-3">
          {listsLoading ? (
            <p className="text-sm text-on-surface-variant animate-pulse">Loading lists...</p>
          ) : userLists.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-on-surface-variant text-sm">No lists yet</p>
              <Link
                to="/lists"
                className="text-primary text-sm font-bold mt-2 inline-block"
                onClick={() => setShowListModal(false)}
              >
                Create your first list
              </Link>
            </div>
          ) : (
            <div className="max-h-64 overflow-y-auto space-y-2">
              {userLists.map((list) => {
                const added = addedToLists.has(list.id);
                return (
                  <div
                    key={list.id}
                    className="flex items-center justify-between p-3 rounded-lg hover:bg-surface-container transition-colors"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-on-surface truncate">{list.name}</p>
                      <p className="text-xs text-on-surface-variant">{list.movie_count} movies</p>
                    </div>
                    {added ? (
                      <span className="text-xs text-primary font-bold uppercase tracking-widest flex items-center gap-1">
                        <span className="material-symbols-outlined text-[16px]">check</span>
                        Added
                      </span>
                    ) : (
                      <button
                        onClick={() => handleAddToList(list.id)}
                        className="text-xs font-bold uppercase tracking-widest text-primary-container hover:text-primary transition-colors"
                      >
                        + Add
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </Modal>
    </>
  );
}
