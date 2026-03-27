import { useCallback, useRef, useSyncExternalStore } from "react";
import { addToWatchlist, removeFromWatchlist, bulkCheckWatchlist } from "../api/watchlist";
import { useUserId } from "./useUserId";

// Module-level state shared across all hook consumers.
let watchlistIds = new Set<number>();
let listeners = new Set<() => void>();

function emitChange() {
  // Create a new Set so React detects the change via referential inequality.
  watchlistIds = new Set(watchlistIds);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return watchlistIds;
}

/**
 * Hook that provides watchlist state and actions.
 * Uses a module-level Set so all components share the same state.
 */
export function useWatchlist() {
  const { userId } = useUserId();
  const ids = useSyncExternalStore(subscribe, getSnapshot);
  // Track in-flight requests to prevent double-toggles.
  const pendingRef = useRef(new Set<number>());

  const isInWatchlist = useCallback(
    (movieId: number) => ids.has(movieId),
    [ids]
  );

  const toggle = useCallback(
    async (movieId: number) => {
      if (pendingRef.current.has(movieId)) return;
      pendingRef.current.add(movieId);

      const wasInWatchlist = watchlistIds.has(movieId);

      // Optimistic update
      if (wasInWatchlist) {
        watchlistIds.delete(movieId);
      } else {
        watchlistIds.add(movieId);
      }
      emitChange();

      try {
        if (wasInWatchlist) {
          await removeFromWatchlist(userId, movieId);
        } else {
          await addToWatchlist(userId, movieId);
        }
      } catch {
        // Rollback on failure
        if (wasInWatchlist) {
          watchlistIds.add(movieId);
        } else {
          watchlistIds.delete(movieId);
        }
        emitChange();
      } finally {
        pendingRef.current.delete(movieId);
      }
    },
    [userId]
  );

  const refreshForMovieIds = useCallback(
    async (movieIds: number[]) => {
      if (movieIds.length === 0) return;
      try {
        const resp = await bulkCheckWatchlist(userId, movieIds);
        // Merge results into the shared set.
        for (const id of movieIds) {
          if (resp.movie_ids.includes(id)) {
            watchlistIds.add(id);
          } else {
            watchlistIds.delete(id);
          }
        }
        emitChange();
      } catch {
        // Silently fail — bookmark state is best-effort
      }
    },
    [userId]
  );

  return { isInWatchlist, toggle, refreshForMovieIds };
}
