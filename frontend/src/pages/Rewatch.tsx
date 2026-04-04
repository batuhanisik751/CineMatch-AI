import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { RewatchItem } from "../api/types";
import { getUserRewatch } from "../api/users";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";

function posterUrl(path: string | null, size = "w300") {
  return path ? `https://image.tmdb.org/t/p/${size}${path}` : null;
}

function yearsAgo(days: number): string {
  const years = Math.floor(days / 365);
  if (years < 1) return "less than a year ago";
  return `${years} year${years > 1 ? "s" : ""} ago`;
}

export default function Rewatch() {
  const { userId } = useUserId();
  const [items, setItems] = useState<RewatchItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    getUserRewatch(userId, 30)
      .then((resp) => setItems(resp.suggestions))
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  }, [userId]);

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-24 pb-32 lg:pl-64">
        <div className="max-w-7xl mx-auto px-6 md:px-10">
          <div className="mb-12">
            <h1 className="text-5xl md:text-6xl font-extrabold font-headline tracking-tighter text-on-surface text-glow">
              REVISIT YOUR FAVORITES
            </h1>
            <p className="text-on-surface-variant mt-3 text-lg">
              Movies you loved long ago that are worth watching again
            </p>
          </div>

          {loading && <LoadingSpinner text="Finding your forgotten favorites..." />}
          {error && <ErrorPanel message={error} />}

          {!loading && !error && items.length === 0 && (
            <div className="text-center py-24">
              <span className="material-symbols-outlined text-6xl text-outline mb-4 block">
                history
              </span>
              <p className="text-on-surface-variant text-lg mb-2">
                No old favorites to revisit yet
              </p>
              <p className="text-on-surface-variant/60 text-sm mb-6">
                Keep rating movies and check back later!
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
                        {/* User rating badge */}
                        <div className="absolute top-4 right-4 bg-primary/90 backdrop-blur-md px-2.5 py-1 rounded flex items-center gap-1">
                          <span
                            className="material-symbols-outlined text-[14px] text-on-primary"
                            style={{ fontVariationSettings: "'FILL' 1" }}
                          >
                            star
                          </span>
                          <span className="text-xs font-bold text-on-primary">
                            {item.user_rating}/10
                          </span>
                        </div>
                        {/* Classic badge */}
                        {item.is_classic && (
                          <div className="absolute top-4 left-4 bg-tertiary/90 backdrop-blur-md px-2 py-1 rounded">
                            <span className="text-[10px] font-bold uppercase tracking-widest text-on-tertiary">
                              Classic
                            </span>
                          </div>
                        )}
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
                            schedule
                          </span>
                          Rated {yearsAgo(item.days_since_rated)}
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
