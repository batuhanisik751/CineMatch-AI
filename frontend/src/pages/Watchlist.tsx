import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getWatchlist, removeFromWatchlist } from "../api/watchlist";
import type { WatchlistItemResponse } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";

function posterUrl(path: string | null, size = "w300") {
  return path ? `https://image.tmdb.org/t/p/${size}${path}` : null;
}

export default function Watchlist() {
  const { userId } = useUserId();
  const [items, setItems] = useState<WatchlistItemResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const limit = 20;

  const fetchWatchlist = () => {
    setLoading(true);
    setError("");
    getWatchlist(userId, offset, limit)
      .then((resp) => {
        setItems(resp.items);
        setTotal(resp.total);
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchWatchlist();
  }, [userId, offset]);

  const handleRemove = async (movieId: number) => {
    try {
      await removeFromWatchlist(userId, movieId);
      setItems((prev) => prev.filter((i) => i.movie_id !== movieId));
      setTotal((prev) => prev - 1);
    } catch {
      // Silently fail — user can retry
    }
  };

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-24 pb-32 lg:pl-64">
        <div className="max-w-7xl mx-auto px-6 md:px-10">
          <div className="mb-12">
            <h1 className="text-5xl md:text-6xl font-extrabold font-headline tracking-tighter text-on-surface text-glow">
              YOUR WATCHLIST
            </h1>
            <p className="text-on-surface-variant mt-3 text-lg">
              {total > 0
                ? `${total} movie${total !== 1 ? "s" : ""} saved for later`
                : "Movies you save will appear here"}
            </p>
          </div>

          {loading && <LoadingSpinner text="Loading watchlist..." />}
          {error && <ErrorPanel message={error} />}

          {!loading && !error && items.length === 0 && (
            <div className="text-center py-24">
              <span className="material-symbols-outlined text-6xl text-outline mb-4 block">
                bookmark
              </span>
              <p className="text-on-surface-variant text-lg mb-6">
                Your watchlist is empty
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
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 xl:grid-cols-5 gap-6">
                {items.map((item) => {
                  const poster = posterUrl(item.poster_path);
                  const year = item.release_date
                    ? new Date(item.release_date).getFullYear()
                    : null;
                  return (
                    <div key={item.movie_id} className="group relative flex flex-col bg-surface-container-low rounded-xl overflow-hidden transition-all duration-300 glow-hover">
                      <Link to={`/movies/${item.movie_id}`}>
                        <div className="aspect-[2/3] overflow-hidden relative">
                          {poster ? (
                            <img
                              src={poster}
                              alt={item.movie_title || "Movie"}
                              className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
                            />
                          ) : (
                            <div className="w-full h-full bg-surface-container flex items-center justify-center">
                              <span className="material-symbols-outlined text-5xl text-outline">
                                movie
                              </span>
                            </div>
                          )}
                          {item.vote_average > 0 && (
                            <div className="absolute top-4 right-4 bg-[#131314]/60 backdrop-blur-md px-2 py-1 rounded flex items-center gap-1 border border-white/10">
                              <span
                                className="material-symbols-outlined text-[14px] text-primary-fixed-dim"
                                style={{ fontVariationSettings: "'FILL' 1" }}
                              >
                                star
                              </span>
                              <span className="text-xs font-bold text-primary">
                                {item.vote_average.toFixed(1)}
                              </span>
                            </div>
                          )}
                        </div>
                        <div className="p-4 flex flex-col gap-2">
                          {year && (
                            <p className="text-xs font-label text-on-surface-variant">
                              {year}
                            </p>
                          )}
                          <h3 className="text-base font-headline font-bold text-on-surface leading-tight group-hover:text-primary transition-colors truncate">
                            {item.movie_title || `Movie #${item.movie_id}`}
                          </h3>
                          <div className="flex flex-wrap gap-1">
                            {item.genres.slice(0, 2).map((g) => (
                              <span
                                key={g}
                                className="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 bg-surface-container-highest text-on-surface-variant rounded"
                              >
                                {g}
                              </span>
                            ))}
                          </div>
                        </div>
                      </Link>
                      <div className="px-4 pb-4">
                        <button
                          onClick={() => handleRemove(item.movie_id)}
                          className="w-full flex items-center justify-center gap-2 py-2 text-xs font-bold uppercase tracking-widest text-error/70 hover:text-error hover:bg-error/10 rounded transition-colors"
                        >
                          <span className="material-symbols-outlined text-[16px]">
                            bookmark_remove
                          </span>
                          Remove
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>

              {totalPages > 1 && (
                <div className="flex justify-center items-center gap-4 mt-12">
                  <button
                    onClick={() => setOffset(Math.max(0, offset - limit))}
                    disabled={offset === 0}
                    className="px-4 py-2 text-sm font-bold text-on-surface-variant hover:text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-on-surface-variant">
                    Page {currentPage} of {totalPages}
                  </span>
                  <button
                    onClick={() => setOffset(offset + limit)}
                    disabled={offset + limit >= total}
                    className="px-4 py-2 text-sm font-bold text-on-surface-variant hover:text-primary disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    Next
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </main>
      <BottomNav />
    </>
  );
}
