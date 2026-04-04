import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { BlindSpotItem } from "../api/types";
import { getUserBlindSpots } from "../api/users";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";

const GENRES = [
  "Action",
  "Comedy",
  "Drama",
  "Horror",
  "Sci-Fi",
  "Thriller",
  "Romance",
  "Animation",
  "Documentary",
  "Crime",
];

function posterUrl(path: string | null, size = "w300") {
  return path ? `https://image.tmdb.org/t/p/${size}${path}` : null;
}

function formatVoteCount(count: number): string {
  if (count >= 1000) return `${(count / 1000).toFixed(count >= 10000 ? 0 : 1)}K`;
  return String(count);
}

export default function BlindSpots() {
  const { userId } = useUserId();
  const [items, setItems] = useState<BlindSpotItem[]>([]);
  const [genre, setGenre] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    getUserBlindSpots(userId, 20, genre)
      .then((resp) => setItems(resp.movies))
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  }, [userId, genre]);

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-24 pb-32 lg:pl-64">
        <div className="max-w-7xl mx-auto px-6 md:px-10">
          <div className="mb-12">
            <h1 className="text-5xl md:text-6xl font-extrabold font-headline tracking-tighter text-on-surface text-glow">
              YOUR CINEMATIC BLIND SPOTS
            </h1>
            <p className="text-on-surface-variant mt-3 text-lg">
              Popular, acclaimed movies you haven't seen yet
            </p>
          </div>

          {/* Genre filter */}
          <div className="flex flex-wrap gap-2 mb-8">
            <button
              onClick={() => setGenre(undefined)}
              className={`px-4 py-2 rounded-full text-sm font-bold transition-all ${
                !genre
                  ? "bg-primary text-on-primary"
                  : "bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest"
              }`}
            >
              All Genres
            </button>
            {GENRES.map((g) => (
              <button
                key={g}
                onClick={() => setGenre(g)}
                className={`px-4 py-2 rounded-full text-sm font-bold transition-all ${
                  genre === g
                    ? "bg-primary text-on-primary"
                    : "bg-surface-container-high text-on-surface-variant hover:bg-surface-container-highest"
                }`}
              >
                {g}
              </button>
            ))}
          </div>

          {loading && <LoadingSpinner text="Scanning your cinematic blind spots..." />}
          {error && <ErrorPanel message={error} />}

          {!loading && !error && items.length === 0 && (
            <div className="text-center py-24">
              <span className="material-symbols-outlined text-6xl text-outline mb-4 block">
                visibility_off
              </span>
              <p className="text-on-surface-variant text-lg mb-2">
                No blind spots found &mdash; impressive!
              </p>
              <p className="text-on-surface-variant/60 text-sm mb-6">
                {genre
                  ? `You've seen all the top ${genre} movies we know about.`
                  : "You've seen all the popular, acclaimed movies."}
              </p>
              <Link
                to="/discover"
                className="inline-block bg-primary-container/20 border border-primary-container/40 text-primary px-6 py-3 rounded-md font-bold hover:bg-primary-container hover:text-on-primary-container transition-all"
              >
                Discover Movies
              </Link>
            </div>
          )}

          {!loading && items.length > 0 && (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-6">
              {items.map((item) => {
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
                        {/* TMDB score badge */}
                        <div className="absolute top-4 right-4 bg-primary/90 backdrop-blur-md px-2.5 py-1 rounded flex items-center gap-1">
                          <span
                            className="material-symbols-outlined text-[14px] text-on-primary"
                            style={{ fontVariationSettings: "'FILL' 1" }}
                          >
                            star
                          </span>
                          <span className="text-xs font-bold text-on-primary">
                            {item.movie.vote_average.toFixed(1)}
                          </span>
                        </div>
                        {/* Vote count badge */}
                        <div className="absolute top-4 left-4 bg-surface/80 backdrop-blur-md px-2 py-1 rounded">
                          <span className="text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
                            {formatVoteCount(item.vote_count)} ratings
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
                            visibility_off
                          </span>
                          Have you seen this?
                        </p>
                      </div>
                    </Link>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>
      <BottomNav />
    </>
  );
}
