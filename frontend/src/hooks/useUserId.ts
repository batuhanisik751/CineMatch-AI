import { useCallback } from "react";
import { useAuth } from "./useAuth";

/**
 * Returns { userId, setUserId } backed by the JWT auth token.
 * Replaces the old random-ID approach. setUserId is a no-op
 * since the userId now comes from the authenticated user's JWT.
 *
 * All 27 files importing this hook continue working without changes.
 */
export function useUserId() {
  const { userId } = useAuth();
  const setUserId = useCallback((_id: number) => {
    // No-op: userId is now derived from the JWT token
  }, []);

  return { userId, setUserId };
}
