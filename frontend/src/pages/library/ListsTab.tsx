import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createList, deleteList, getUserLists, updateList } from "../../api/lists";
import type { UserListSummary } from "../../api/types";
import ErrorPanel from "../../components/ErrorPanel";
import LoadingSpinner from "../../components/LoadingSpinner";
import Modal from "../../components/Modal";
import { useUserId } from "../../hooks/useUserId";

const TMDB_IMG = "https://image.tmdb.org/t/p/w200";

export default function ListsTab() {
  const { userId } = useUserId();
  const [lists, setLists] = useState<UserListSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // Create / Edit modal
  const [showModal, setShowModal] = useState(false);
  const [editingList, setEditingList] = useState<UserListSummary | null>(null);
  const [formName, setFormName] = useState("");
  const [formDesc, setFormDesc] = useState("");
  const [formPublic, setFormPublic] = useState(false);
  const [saving, setSaving] = useState(false);

  // Delete confirm
  const [deleteTarget, setDeleteTarget] = useState<UserListSummary | null>(null);

  const fetchLists = () => {
    setLoading(true);
    setError("");
    getUserLists(userId)
      .then((resp) => setLists(resp.lists))
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchLists();
  }, [userId]);

  const openCreate = () => {
    setEditingList(null);
    setFormName("");
    setFormDesc("");
    setFormPublic(false);
    setShowModal(true);
  };

  const openEdit = (list: UserListSummary) => {
    setEditingList(list);
    setFormName(list.name);
    setFormDesc(list.description || "");
    setFormPublic(list.is_public);
    setShowModal(true);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) return;
    setSaving(true);
    try {
      if (editingList) {
        const updated = await updateList(userId, editingList.id, {
          name: formName.trim(),
          description: formDesc.trim() || undefined,
          is_public: formPublic,
        });
        setLists((prev) =>
          prev.map((l) => (l.id === editingList.id ? { ...l, ...updated } : l)),
        );
      } else {
        const created = await createList(
          userId,
          formName.trim(),
          formDesc.trim() || undefined,
          formPublic,
        );
        setLists((prev) => [created, ...prev]);
      }
      setShowModal(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteList(userId, deleteTarget.id);
      setLists((prev) => prev.filter((l) => l.id !== deleteTarget.id));
    } catch {
      // silent
    }
    setDeleteTarget(null);
  };

  return (
    <>
      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-5xl md:text-6xl font-extrabold font-headline tracking-tighter text-on-surface text-glow">
            MY LISTS
          </h1>
          <div className="flex gap-2">
            <Link
              to="/library/lists/popular"
              className="hidden sm:flex items-center gap-2 bg-surface-container-low border border-white/10 text-on-surface-variant px-4 py-2.5 rounded-lg text-xs font-bold uppercase tracking-widest hover:bg-surface-container hover:text-on-surface transition-all"
            >
              <span className="material-symbols-outlined text-[18px]">public</span>
              Browse Public
            </Link>
            <button
              onClick={openCreate}
              className="flex items-center gap-2 bg-primary-container text-on-primary-container px-5 py-2.5 rounded-lg text-xs font-bold uppercase tracking-widest hover:brightness-110 transition-all"
            >
              <span className="material-symbols-outlined text-[18px]">add</span>
              New List
            </button>
          </div>
        </div>
        <p className="text-on-surface-variant text-lg">
          {lists.length > 0
            ? `${lists.length} collection${lists.length !== 1 ? "s" : ""}`
            : "Create and organize your movie collections"}
        </p>
      </div>

      {loading && <LoadingSpinner text="Loading your lists..." />}
      {error && <ErrorPanel message={error} onRetry={fetchLists} />}

      {/* Empty state */}
      {!loading && !error && lists.length === 0 && (
        <div className="text-center py-24">
          <span className="material-symbols-outlined text-6xl text-outline mb-4 block">
            playlist_add
          </span>
          <p className="text-on-surface-variant text-lg mb-2">
            No lists yet
          </p>
          <p className="text-on-surface-variant/60 text-sm mb-6">
            Group your favorite movies into collections
          </p>
          <button
            onClick={openCreate}
            className="inline-block bg-primary-container/20 border border-primary-container/40 text-primary px-6 py-3 rounded-md font-bold hover:bg-primary-container hover:text-on-primary-container transition-all"
          >
            Create Your First List
          </button>
        </div>
      )}

      {/* Lists */}
      {!loading && !error && lists.length > 0 && (
        <div className="space-y-4">
          {lists.map((list) => (
            <Link
              key={list.id}
              to={`/library/lists/${list.id}`}
              className="group flex items-center gap-5 glass-card rounded-xl p-4 md:p-5 transition-all duration-300 glow-hover"
            >
              {/* Poster previews */}
              <div className="flex-shrink-0 w-28 h-20 md:w-36 md:h-24 rounded-lg overflow-hidden bg-surface-container-low flex">
                {list.preview_posters.length > 0 ? (
                  list.preview_posters.slice(0, 4).map((p, i) => (
                    <img
                      key={i}
                      src={`${TMDB_IMG}${p}`}
                      alt=""
                      className="h-full flex-1 object-cover"
                    />
                  ))
                ) : (
                  <div className="flex items-center justify-center w-full text-on-surface-variant/20">
                    <span className="material-symbols-outlined text-3xl">
                      movie
                    </span>
                  </div>
                )}
              </div>

              {/* Info */}
              <div className="flex-1 min-w-0">
                <h3 className="text-lg md:text-xl font-headline font-bold text-on-surface group-hover:text-primary transition-colors truncate">
                  {list.name}
                </h3>
                {list.description && (
                  <p className="text-sm text-on-surface-variant line-clamp-1 mt-0.5">
                    {list.description}
                  </p>
                )}
                <div className="flex items-center gap-3 mt-2 text-xs text-on-surface-variant">
                  <span className="flex items-center gap-1">
                    <span className="material-symbols-outlined text-[14px]">
                      movie
                    </span>
                    {list.movie_count} movie{list.movie_count !== 1 ? "s" : ""}
                  </span>
                  {list.is_public && (
                    <span className="flex items-center gap-1 text-primary">
                      <span className="material-symbols-outlined text-[14px]">
                        public
                      </span>
                      Public
                    </span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex-shrink-0 flex items-center gap-1">
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    openEdit(list);
                  }}
                  className="p-2 rounded-lg text-on-surface-variant hover:text-on-surface hover:bg-surface-container transition-colors"
                  title="Edit list"
                >
                  <span className="material-symbols-outlined text-[20px]">
                    edit
                  </span>
                </button>
                <button
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setDeleteTarget(list);
                  }}
                  className="p-2 rounded-lg text-on-surface-variant hover:text-error hover:bg-error/10 transition-colors"
                  title="Delete list"
                >
                  <span className="material-symbols-outlined text-[20px]">
                    delete
                  </span>
                </button>
                <span className="material-symbols-outlined text-[20px] text-on-surface-variant/30 ml-1">
                  chevron_right
                </span>
              </div>
            </Link>
          ))}

          {/* Mobile link to popular lists */}
          <Link
            to="/library/lists/popular"
            className="sm:hidden flex items-center justify-center gap-2 glass-card rounded-xl p-4 text-on-surface-variant hover:text-primary transition-colors"
          >
            <span className="material-symbols-outlined text-[18px]">public</span>
            <span className="text-sm font-bold uppercase tracking-widest">
              Browse Public Lists
            </span>
          </Link>
        </div>
      )}

      {/* Create / Edit modal */}
      <Modal
        isOpen={showModal}
        title={editingList ? "Edit List" : "New List"}
        onClose={() => setShowModal(false)}
      >
        <form onSubmit={handleSave} className="space-y-4">
          <div>
            <label className="text-sm text-on-surface-variant block mb-1">
              Name
            </label>
            <input
              type="text"
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              maxLength={200}
              placeholder="e.g. Best Sci-Fi Ever"
              className="w-full bg-surface-container border border-white/10 rounded-lg px-4 py-3 text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-primary-container"
              autoFocus
            />
          </div>
          <div>
            <label className="text-sm text-on-surface-variant block mb-1">
              Description (optional)
            </label>
            <textarea
              value={formDesc}
              onChange={(e) => setFormDesc(e.target.value)}
              rows={2}
              placeholder="What's this list about?"
              className="w-full bg-surface-container border border-white/10 rounded-lg px-4 py-3 text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:border-primary-container resize-none"
            />
          </div>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={formPublic}
              onChange={(e) => setFormPublic(e.target.checked)}
              className="w-4 h-4 accent-primary-container"
            />
            <span className="text-sm text-on-surface-variant">
              Make this list public
            </span>
          </label>
          <button
            type="submit"
            disabled={!formName.trim() || saving}
            className="w-full bg-primary-container text-on-primary-container py-3 rounded-lg font-bold text-sm uppercase tracking-widest hover:brightness-110 transition-all disabled:opacity-40"
          >
            {saving
              ? "Saving..."
              : editingList
                ? "Save Changes"
                : "Create List"}
          </button>
        </form>
      </Modal>

      {/* Delete confirmation */}
      <Modal
        isOpen={deleteTarget !== null}
        title="Delete List"
        onClose={() => setDeleteTarget(null)}
      >
        <p className="text-on-surface-variant">
          Are you sure you want to delete{" "}
          <span className="text-on-surface font-bold">
            {deleteTarget?.name}
          </span>
          ? This will remove all movies from the list. This cannot be undone.
        </p>
        <div className="flex gap-3 mt-6">
          <button
            onClick={() => setDeleteTarget(null)}
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
