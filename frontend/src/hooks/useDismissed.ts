import { useCallback, useRef, useSyncExternalStore } from "react";
import { dismissMovie, undismissMovie, bulkCheckDismissals } from "../api/dismissals";
import { useUserId } from "./useUserId";

// Module-level state shared across all hook consumers.
let dismissedIds = new Set<number>();
let listeners = new Set<() => void>();

function emitChange() {
  // Create a new Set so React detects the change via referential inequality.
  dismissedIds = new Set(dismissedIds);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return dismissedIds;
}

/**
 * Hook that provides dismissed/not-interested state and actions.
 * Uses a module-level Set so all components share the same state.
 */
export function useDismissed() {
  const { userId } = useUserId();
  const ids = useSyncExternalStore(subscribe, getSnapshot);
  // Track in-flight requests to prevent double-toggles.
  const pendingRef = useRef(new Set<number>());

  const isDismissed = useCallback(
    (movieId: number) => ids.has(movieId),
    [ids]
  );

  const toggleDismiss = useCallback(
    async (movieId: number) => {
      if (pendingRef.current.has(movieId)) return;
      pendingRef.current.add(movieId);

      const wasDismissed = dismissedIds.has(movieId);

      // Optimistic update
      if (wasDismissed) {
        dismissedIds.delete(movieId);
      } else {
        dismissedIds.add(movieId);
      }
      emitChange();

      try {
        if (wasDismissed) {
          await undismissMovie(userId, movieId);
        } else {
          await dismissMovie(userId, movieId);
        }
      } catch {
        // Rollback on failure
        if (wasDismissed) {
          dismissedIds.add(movieId);
        } else {
          dismissedIds.delete(movieId);
        }
        emitChange();
      } finally {
        pendingRef.current.delete(movieId);
      }
    },
    [userId]
  );

  const refreshDismissedForMovieIds = useCallback(
    async (movieIds: number[]) => {
      if (movieIds.length === 0) return;
      try {
        const resp = await bulkCheckDismissals(userId, movieIds);
        // Merge results into the shared set.
        for (const id of movieIds) {
          if (resp.movie_ids.includes(id)) {
            dismissedIds.add(id);
          } else {
            dismissedIds.delete(id);
          }
        }
        emitChange();
      } catch {
        // Silently fail — dismissal state is best-effort
      }
    },
    [userId]
  );

  return { isDismissed, toggleDismiss, refreshDismissedForMovieIds };
}
