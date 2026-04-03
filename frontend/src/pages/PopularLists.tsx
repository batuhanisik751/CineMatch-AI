import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getPopularLists } from "../api/lists";
import type { UserListSummary } from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";

const TMDB_IMG = "https://image.tmdb.org/t/p/w200";

export default function PopularLists() {
  const [lists, setLists] = useState<UserListSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const limit = 20;

  const fetchLists = () => {
    setLoading(true);
    setError("");
    getPopularLists(offset, limit)
      .then((resp) => {
        setLists(resp.lists);
        setTotal(resp.total);
      })
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLists();
  }, [offset]);

  const totalPages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-24 pb-32 lg:pl-64">
        <div className="max-w-7xl mx-auto px-6 md:px-10">
          {/* Header */}
          <div className="mb-10">
            <Link
              to="/library/lists"
              className="text-on-surface-variant text-xs uppercase tracking-widest hover:text-primary transition-colors mb-3 inline-flex items-center gap-1"
            >
              <span className="material-symbols-outlined text-[16px]">arrow_back</span>
              My Lists
            </Link>
            <h1 className="text-5xl md:text-6xl font-extrabold font-headline tracking-tighter text-on-surface text-glow">
              POPULAR LISTS
            </h1>
            <p className="text-on-surface-variant text-lg mt-1">
              Public collections from the community
            </p>
          </div>

          {loading && <LoadingSpinner text="Loading popular lists..." />}
          {error && <ErrorPanel message={error} onRetry={fetchLists} />}

          {!loading && !error && lists.length === 0 && (
            <div className="text-center py-24">
              <span className="material-symbols-outlined text-6xl text-outline mb-4 block">
                public
              </span>
              <p className="text-on-surface-variant text-lg">
                No public lists yet
              </p>
              <p className="text-on-surface-variant/60 text-sm mt-1">
                Be the first to share a collection!
              </p>
            </div>
          )}

          {!loading && !error && lists.length > 0 && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {lists.map((list) => (
                  <Link
                    key={list.id}
                    to={`/library/lists/${list.id}`}
                    className="group glass-card rounded-xl overflow-hidden transition-all duration-300 glow-hover"
                  >
                    <div className="h-32 bg-surface-container-low flex overflow-hidden">
                      {list.preview_posters.length > 0 ? (
                        list.preview_posters.map((p, i) => (
                          <img
                            key={i}
                            src={`${TMDB_IMG}${p}`}
                            alt=""
                            className="h-full flex-1 object-cover"
                          />
                        ))
                      ) : (
                        <div className="flex items-center justify-center w-full text-on-surface-variant/20">
                          <span className="material-symbols-outlined text-5xl">
                            movie
                          </span>
                        </div>
                      )}
                    </div>

                    <div className="p-5 space-y-2">
                      <h3 className="text-lg font-headline font-bold text-on-surface group-hover:text-primary transition-colors">
                        {list.name}
                      </h3>
                      {list.description && (
                        <p className="text-sm text-on-surface-variant line-clamp-2">
                          {list.description}
                        </p>
                      )}
                      <div className="flex items-center gap-3 text-xs text-on-surface-variant">
                        <span className="flex items-center gap-1">
                          <span className="material-symbols-outlined text-[14px]">
                            movie
                          </span>
                          {list.movie_count} movies
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="material-symbols-outlined text-[14px]">
                            person
                          </span>
                          User #{list.user_id}
                        </span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>

              {/* Pagination */}
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
                    disabled={currentPage >= totalPages}
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
