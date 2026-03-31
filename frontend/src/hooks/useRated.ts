import { useCallback, useSyncExternalStore } from "react";
import { bulkCheckRatings } from "../api/ratings";
import { useUserId } from "./useUserId";

// Module-level state shared across all hook consumers.
let ratedMap = new Map<number, number>();
let listeners = new Set<() => void>();

function emitChange() {
  // Create a new Map so React detects the change via referential inequality.
  ratedMap = new Map(ratedMap);
  listeners.forEach((l) => l());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function getSnapshot() {
  return ratedMap;
}

/**
 * Hook that provides user rating state and actions.
 * Uses a module-level Map so all components share the same state.
 */
export function useRated() {
  const { userId } = useUserId();
  const map = useSyncExternalStore(subscribe, getSnapshot);

  const getRating = useCallback(
    (movieId: number): number | null => {
      return map.get(movieId) ?? null;
    },
    [map]
  );

  const isRated = useCallback(
    (movieId: number): boolean => {
      return map.has(movieId);
    },
    [map]
  );

  const refreshRatingsForMovieIds = useCallback(
    async (movieIds: number[]) => {
      if (movieIds.length === 0) return;
      try {
        const resp = await bulkCheckRatings(userId, movieIds);
        // Merge results into the shared map.
        for (const id of movieIds) {
          const rating = resp.ratings[id];
          if (rating != null) {
            ratedMap.set(id, rating);
          } else {
            ratedMap.delete(id);
          }
        }
        emitChange();
      } catch {
        // Silently fail — rating state is best-effort
      }
    },
    [userId]
  );

  const setLocalRating = useCallback((movieId: number, rating: number) => {
    ratedMap.set(movieId, rating);
    emitChange();
  }, []);

  return { getRating, isRated, refreshRatingsForMovieIds, setLocalRating };
}
