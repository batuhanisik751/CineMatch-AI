import { useCallback, useSyncExternalStore } from "react";
import { getBatchPredictedMatches } from "../api/predictions";
import { useUserId } from "./useUserId";

// Module-level state shared across all hook consumers.
let matchMap = new Map<number, number>();
let listeners = new Set<() => void>();
let pendingIds = new Set<number>();
let lastUserId: number | null = null;

function emitChange() {
  matchMap = new Map(matchMap);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return matchMap;
}

/**
 * Hook that provides predicted match percentages for movies.
 * Uses a module-level Map so all components share the same state.
 */
export function useMatchPredictions() {
  const { userId } = useUserId();
  const map = useSyncExternalStore(subscribe, getSnapshot);

  // Clear cache when user changes
  if (userId !== lastUserId) {
    lastUserId = userId;
    matchMap = new Map();
    pendingIds = new Set();
    emitChange();
  }

  const getMatchPercent = useCallback(
    (movieId: number): number | undefined => {
      return map.get(movieId);
    },
    [map]
  );

  const fetchMatchPercents = useCallback(
    async (movieIds: number[]) => {
      // Filter out already loaded and in-flight IDs
      const needed = movieIds.filter(
        (id) => !matchMap.has(id) && !pendingIds.has(id)
      );
      if (needed.length === 0) return;

      // Mark as pending to deduplicate concurrent requests
      for (const id of needed) pendingIds.add(id);

      try {
        const resp = await getBatchPredictedMatches(userId, needed);
        for (const p of resp.predictions) {
          matchMap.set(p.movie_id, p.match_percent);
        }
        emitChange();
      } catch {
        // Silently fail — match predictions are best-effort
      } finally {
        for (const id of needed) pendingIds.delete(id);
      }
    },
    [userId]
  );

  return { getMatchPercent, fetchMatchPercents };
}
