import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { getMovie, getSimilarMovies } from "../api/movies";
import { addRating } from "../api/ratings";
import type { MovieResponse, SimilarMovie } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import StarRating from "../components/StarRating";
import TopNav from "../components/TopNav";
import { useRated } from "../hooks/useRated";
import { useUserId } from "../hooks/useUserId";
import { useWatchlist } from "../hooks/useWatchlist";

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

  const handleRate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (userRating === 0 || !movie) return;
    try {
      await addRating(userId, movie.id, userRating);
      setLocalRating(movie.id, userRating);
      setRatingMsg("Rating submitted!");
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
              <div className="grid grid-cols-2 md:grid-cols-4 gap-8 pb-12 border-b border-outline-variant/10">
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
      </main>
      <BottomNav />
    </>
  );
}
