import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { addMovieToList, getUserLists } from "../api/lists";
import type { UserListSummary } from "../api/types";
import { useUserId } from "../hooks/useUserId";
import Modal from "./Modal";

interface Props {
  movieId: number | null;
  onClose: () => void;
}

export default function AddToListModal({ movieId, onClose }: Props) {
  const { userId } = useUserId();
  const [lists, setLists] = useState<UserListSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [addedTo, setAddedTo] = useState<Set<number>>(new Set());

  useEffect(() => {
    if (movieId === null) return;
    setLoading(true);
    setAddedTo(new Set());
    getUserLists(userId)
      .then((resp) => setLists(resp.lists))
      .catch(() => setLists([]))
      .finally(() => setLoading(false));
  }, [movieId, userId]);

  const handleAdd = async (listId: number) => {
    if (movieId === null) return;
    try {
      await addMovieToList(userId, listId, movieId);
      setAddedTo((prev) => new Set([...prev, listId]));
    } catch {
      // silent
    }
  };

  return (
    <Modal isOpen={movieId !== null} title="Add to List" onClose={onClose}>
      <div className="space-y-3">
        {loading ? (
          <p className="text-sm text-on-surface-variant animate-pulse">
            Loading lists...
          </p>
        ) : lists.length === 0 ? (
          <div className="text-center py-6">
            <span className="material-symbols-outlined text-4xl text-on-surface-variant/30 block mb-2">
              playlist_add
            </span>
            <p className="text-on-surface-variant text-sm">No lists yet</p>
            <Link
              to="/lists"
              onClick={onClose}
              className="text-primary text-sm font-bold mt-2 inline-block hover:underline"
            >
              Create your first list &rarr;
            </Link>
          </div>
        ) : (
          <div className="max-h-72 overflow-y-auto space-y-1">
            {lists.map((list) => {
              const added = addedTo.has(list.id);
              return (
                <div
                  key={list.id}
                  className="flex items-center justify-between p-3 rounded-lg hover:bg-surface-container transition-colors"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium text-on-surface truncate">
                      {list.name}
                    </p>
                    <p className="text-xs text-on-surface-variant">
                      {list.movie_count} movie{list.movie_count !== 1 ? "s" : ""}
                      {list.is_public && " · Public"}
                    </p>
                  </div>
                  {added ? (
                    <span className="flex items-center gap-1 text-xs text-primary font-bold uppercase tracking-widest">
                      <span className="material-symbols-outlined text-[16px]">
                        check
                      </span>
                      Added
                    </span>
                  ) : (
                    <button
                      onClick={() => handleAdd(list.id)}
                      className="flex items-center gap-1 text-xs font-bold uppercase tracking-widest text-primary-container hover:text-primary transition-colors"
                    >
                      <span className="material-symbols-outlined text-[16px]">
                        add
                      </span>
                      Add
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Modal>
  );
}
