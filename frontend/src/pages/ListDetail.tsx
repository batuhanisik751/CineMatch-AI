import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  addMovieToList,
  deleteList,
  getList,
  removeMovieFromList,
  reorderListItems,
  updateList,
} from "../api/lists";
import { searchMovies } from "../api/movies";
import type {
  MovieSummary,
  UserListDetailResponse,
  UserListItemResponse,
} from "../api/types";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import Modal from "../components/Modal";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";

const TMDB_IMG = "https://image.tmdb.org/t/p/w200";

function searchMovies_(query: string) {
  return searchMovies(query, 10);
}

export default function ListDetail() {
  const { id } = useParams<{ id: string }>();
  const listId = Number(id);
  const { userId } = useUserId();
  const navigate = useNavigate();

  const [list, setList] = useState<UserListDetailResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Edit modal
  const [showEdit, setShowEdit] = useState(false);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");
  const [editPublic, setEditPublic] = useState(false);

  // Add movie
  const [showAddMovie, setShowAddMovie] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<MovieSummary[]>([]);
  const [searching, setSearching] = useState(false);

  // Delete confirm
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const isOwner = list?.user_id === userId;

  const fetchList = () => {
    setLoading(true);
    setError("");
    getList(listId)
      .then((resp) => {
        setList(resp);
        setEditName(resp.name);
        setEditDesc(resp.description || "");
        setEditPublic(resp.is_public);
      })
      .catch((e) => setError(typeof e.detail === "string" ? e.detail : e.message || "Failed to load list"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchList();
  }, [listId]);

  // Search debounce
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      return;
    }
    const timer = setTimeout(() => {
      setSearching(true);
      searchMovies_(searchQuery.trim())
        .then((resp) => setSearchResults(resp.results))
        .catch(() => setSearchResults([]))
        .finally(() => setSearching(false));
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!list || !editName.trim()) return;
    try {
      await updateList(userId, listId, {
        name: editName.trim(),
        description: editDesc.trim() || undefined,
        is_public: editPublic,
      });
      setList({
        ...list,
        name: editName.trim(),
        description: editDesc.trim() || null,
        is_public: editPublic,
      });
      setShowEdit(false);
    } catch {
      // silent
    }
  };

  const handleDelete = async () => {
    try {
      await deleteList(userId, listId);
      navigate("/lists");
    } catch {
      // silent
    }
  };

  const handleAddMovie = async (movieId: number) => {
    if (!list) return;
    try {
      const item = await addMovieToList(userId, listId, movieId);
      setList({
        ...list,
        items: [...list.items, item],
        movie_count: list.movie_count + 1,
        total: list.total + 1,
      });
    } catch {
      // silent
    }
  };

  const handleRemoveMovie = async (movieId: number) => {
    if (!list) return;
    try {
      await removeMovieFromList(userId, listId, movieId);
      setList({
        ...list,
        items: list.items.filter((i) => i.movie_id !== movieId),
        movie_count: list.movie_count - 1,
        total: list.total - 1,
      });
    } catch {
      // silent
    }
  };

  const handleMoveUp = async (index: number) => {
    if (!list || index === 0) return;
    const newItems = [...list.items];
    [newItems[index - 1], newItems[index]] = [newItems[index], newItems[index - 1]];
    setList({ ...list, items: newItems });
    try {
      await reorderListItems(
        userId,
        listId,
        newItems.map((i) => i.movie_id),
      );
    } catch {
      fetchList();
    }
  };

  const handleMoveDown = async (index: number) => {
    if (!list || index === list.items.length - 1) return;
    const newItems = [...list.items];
    [newItems[index], newItems[index + 1]] = [newItems[index + 1], newItems[index]];
    setList({ ...list, items: newItems });
    try {
      await reorderListItems(
        userId,
        listId,
        newItems.map((i) => i.movie_id),
      );
    } catch {
      fetchList();
    }
  };

  const existingMovieIds = list
    ? new Set(list.items.map((i) => i.movie_id))
    : new Set<number>();

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-24 pb-32 lg:pl-64">
        <div className="max-w-7xl mx-auto px-6 md:px-10">
          {loading && <LoadingSpinner text="Loading list..." />}
          {error && <ErrorPanel message={error} onRetry={fetchList} />}

          {!loading && !error && !list && (
            <ErrorPanel message="List not found" />
          )}

          {!loading && !error && list && (
            <>
              {/* Header */}
              <div className="mb-10">
                <Link
                  to="/lists"
                  className="text-on-surface-variant text-xs uppercase tracking-widest hover:text-primary transition-colors mb-3 inline-flex items-center gap-1"
                >
                  <span className="material-symbols-outlined text-[16px]">
                    arrow_back
                  </span>
                  My Lists
                </Link>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <h1 className="text-5xl md:text-6xl font-extrabold font-headline tracking-tighter text-on-surface text-glow">
                      {list.name.toUpperCase()}
                    </h1>
                    {list.description && (
                      <p className="text-on-surface-variant text-lg mt-2">
                        {list.description}
                      </p>
                    )}
                    <div className="flex items-center gap-4 mt-3 text-on-surface-variant">
                      <span>
                        {list.movie_count} movie
                        {list.movie_count !== 1 ? "s" : ""}
                      </span>
                      {list.is_public && (
                        <span className="flex items-center gap-1 text-primary text-sm">
                          <span className="material-symbols-outlined text-[16px]">
                            public
                          </span>
                          Public
                        </span>
                      )}
                    </div>
                  </div>

                  {isOwner && (
                    <div className="flex gap-2 flex-shrink-0 mt-2">
                      <button
                        onClick={() => setShowAddMovie(true)}
                        className="flex items-center gap-2 bg-primary-container text-on-primary-container px-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-widest hover:brightness-110 transition-all"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          add
                        </span>
                        <span className="hidden sm:inline">Add Movies</span>
                      </button>
                      <button
                        onClick={() => setShowEdit(true)}
                        className="p-2.5 rounded-lg bg-surface-container-low border border-white/10 text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-all"
                        title="Edit list"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          edit
                        </span>
                      </button>
                      <button
                        onClick={() => setShowDeleteConfirm(true)}
                        className="p-2.5 rounded-lg bg-error/10 border border-error/20 text-error hover:bg-error/20 transition-all"
                        title="Delete list"
                      >
                        <span className="material-symbols-outlined text-[18px]">
                          delete
                        </span>
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Movie items */}
              {list.items.length === 0 ? (
                <div className="text-center py-24">
                  <span className="material-symbols-outlined text-6xl text-outline mb-4 block">
                    movie
                  </span>
                  <p className="text-on-surface-variant text-lg">
                    No movies in this list yet
                  </p>
                  {isOwner && (
                    <button
                      onClick={() => setShowAddMovie(true)}
                      className="mt-6 inline-block bg-primary-container/20 border border-primary-container/40 text-primary px-6 py-3 rounded-md font-bold hover:bg-primary-container hover:text-on-primary-container transition-all"
                    >
                      Add Movies
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-3">
                  {list.items.map((item, index) => (
                    <ListMovieRow
                      key={item.movie_id}
                      item={item}
                      index={index}
                      total={list.items.length}
                      isOwner={isOwner}
                      onRemove={() => handleRemoveMovie(item.movie_id)}
                      onMoveUp={() => handleMoveUp(index)}
                      onMoveDown={() => handleMoveDown(index)}
                    />
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </main>
      <BottomNav />

      {/* Edit modal */}
      <Modal
        isOpen={showEdit}
        title="Edit List"
        onClose={() => setShowEdit(false)}
      >
        <form onSubmit={handleUpdate} className="space-y-4">
          <div>
            <label className="text-sm text-on-surface-variant block mb-1">
              Name
            </label>
            <input
              type="text"
              value={editName}
              onChange={(e) => setEditName(e.target.value)}
              maxLength={200}
              className="w-full bg-surface-container border border-white/10 rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-primary-container"
              autoFocus
            />
          </div>
          <div>
            <label className="text-sm text-on-surface-variant block mb-1">
              Description
            </label>
            <textarea
              value={editDesc}
              onChange={(e) => setEditDesc(e.target.value)}
              rows={2}
              className="w-full bg-surface-container border border-white/10 rounded-lg px-4 py-3 text-on-surface focus:outline-none focus:border-primary-container resize-none"
            />
          </div>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={editPublic}
              onChange={(e) => setEditPublic(e.target.checked)}
              className="w-4 h-4 accent-primary-container"
            />
            <span className="text-sm text-on-surface-variant">Public</span>
          </label>
          <button
            type="submit"
            disabled={!editName.trim()}
            className="w-full bg-primary-container text-on-primary-container py-3 rounded-lg font-bold text-sm uppercase tracking-widest hover:brightness-110 transition-all disabled:opacity-40"
          >
            Save Changes
          </button>
        </form>
      </Modal>

      {/* Add movie modal */}
      <Modal
        isOpen={showAddMovie}
        title="Add Movies"
        onClose={() => {
          setShowAddMovie(false);
          setSearchQuery("");
          setSearchResults([]);
        }}
      >
        <div className="space-y-4">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search for a movie..."
            className="w-full bg-surface-container border border-white/10 rounded-lg px-4 py-3 text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-primary-container"
            autoFocus
          />
          {searching && (
            <p className="text-sm text-on-surface-variant animate-pulse">
              Searching...
            </p>
          )}
          <div className="max-h-64 overflow-y-auto space-y-2">
            {searchResults.map((movie) => {
              const alreadyAdded = existingMovieIds.has(movie.id);
              return (
                <div
                  key={movie.id}
                  className="flex items-center gap-3 p-2 rounded-lg hover:bg-surface-container transition-colors"
                >
                  {movie.poster_path ? (
                    <img
                      src={`${TMDB_IMG}${movie.poster_path}`}
                      alt=""
                      className="w-10 h-14 rounded object-cover"
                    />
                  ) : (
                    <div className="w-10 h-14 rounded bg-surface-container-low flex items-center justify-center">
                      <span className="material-symbols-outlined text-[16px] text-on-surface-variant/30">
                        movie
                      </span>
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-on-surface truncate">
                      {movie.title}
                    </p>
                    <p className="text-xs text-on-surface-variant">
                      {movie.release_date?.slice(0, 4) || "N/A"}
                    </p>
                  </div>
                  {alreadyAdded ? (
                    <span className="text-xs text-primary font-bold uppercase tracking-widest">
                      Added
                    </span>
                  ) : (
                    <button
                      onClick={() => handleAddMovie(movie.id)}
                      className="text-xs font-bold uppercase tracking-widest text-primary-container hover:text-primary transition-colors"
                    >
                      + Add
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </Modal>

      {/* Delete confirmation */}
      <Modal
        isOpen={showDeleteConfirm}
        title="Delete List"
        onClose={() => setShowDeleteConfirm(false)}
      >
        <p className="text-on-surface-variant">
          Are you sure you want to delete{" "}
          <span className="text-on-surface font-bold">{list?.name}</span>? This
          will remove all movies from the list. This cannot be undone.
        </p>
        <div className="flex gap-3 mt-6">
          <button
            onClick={() => setShowDeleteConfirm(false)}
            className="flex-1 bg-surface-container border border-white/10 text-on-surface-variant py-3 rounded-lg font-bold text-sm uppercase tracking-widest hover:bg-surface-container-high transition-all"
          >
            Cancel
          </button>
          <button
            onClick={handleDelete}
            className="flex-1 bg-error/20 border border-error/30 text-error py-3 rounded-lg font-bold text-sm uppercase tracking-widest hover:bg-error/30 transition-all"
          >
            Delete
          </button>
        </div>
      </Modal>
    </>
  );
}

function ListMovieRow({
  item,
  index,
  total,
  isOwner,
  onRemove,
  onMoveUp,
  onMoveDown,
}: {
  item: UserListItemResponse;
  index: number;
  total: number;
  isOwner: boolean;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}) {
  return (
    <div className="flex items-center gap-4 glass-card rounded-xl p-4 group">
      <span className="text-2xl font-headline font-black text-on-surface-variant/30 w-8 text-center flex-shrink-0">
        {index + 1}
      </span>

      <Link to={`/movies/${item.movie_id}`} className="flex-shrink-0">
        {item.poster_path ? (
          <img
            src={`${TMDB_IMG}${item.poster_path}`}
            alt=""
            className="w-12 h-18 rounded object-cover"
          />
        ) : (
          <div className="w-12 h-18 rounded bg-surface-container-low flex items-center justify-center">
            <span className="material-symbols-outlined text-on-surface-variant/30">
              movie
            </span>
          </div>
        )}
      </Link>

      <div className="flex-1 min-w-0">
        <Link
          to={`/movies/${item.movie_id}`}
          className="font-headline font-bold text-on-surface hover:text-primary transition-colors truncate block"
        >
          {item.movie_title || `Movie #${item.movie_id}`}
        </Link>
        <div className="flex items-center gap-3 text-xs text-on-surface-variant mt-1">
          {item.release_date && <span>{item.release_date.slice(0, 4)}</span>}
          {item.genres.length > 0 && (
            <span>{item.genres.slice(0, 2).join(", ")}</span>
          )}
          {item.vote_average > 0 && (
            <span className="flex items-center gap-0.5">
              <span
                className="material-symbols-outlined text-[12px] text-primary"
                style={{ fontVariationSettings: "'FILL' 1" }}
              >
                star
              </span>
              {item.vote_average.toFixed(1)}
            </span>
          )}
        </div>
      </div>

      {isOwner && (
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onMoveUp}
            disabled={index === 0}
            className="p-1 text-on-surface-variant hover:text-on-surface disabled:opacity-20 transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">
              arrow_upward
            </span>
          </button>
          <button
            onClick={onMoveDown}
            disabled={index === total - 1}
            className="p-1 text-on-surface-variant hover:text-on-surface disabled:opacity-20 transition-colors"
          >
            <span className="material-symbols-outlined text-[20px]">
              arrow_downward
            </span>
          </button>
          <button
            onClick={onRemove}
            className="p-1 text-error/50 hover:text-error transition-colors ml-2"
          >
            <span className="material-symbols-outlined text-[20px]">
              close
            </span>
          </button>
        </div>
      )}
    </div>
  );
}
