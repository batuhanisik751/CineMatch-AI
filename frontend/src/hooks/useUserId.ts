import { useCallback, useSyncExternalStore } from "react";

const STORAGE_KEY = "cinematch_user_id";

/**
 * Generate a random user ID in a range that won't collide with
 * MovieLens dataset users (which go up to ~162K).
 * Range: 200_000 – 999_999
 */
function generateUserId(): number {
  return 200_000 + Math.floor(Math.random() * 800_000);
}

function getStoredId(): number {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (raw) {
    const parsed = Number(raw);
    if (!Number.isNaN(parsed) && parsed > 0) return parsed;
  }
  const id = generateUserId();
  localStorage.setItem(STORAGE_KEY, String(id));
  return id;
}

// Keep an in-memory copy so all subscribers share the same value.
let currentId = 0;

function subscribe(callback: () => void) {
  const handler = (e: StorageEvent) => {
    if (e.key === STORAGE_KEY) {
      currentId = getStoredId();
      callback();
    }
  };
  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}

function getSnapshot(): number {
  if (currentId === 0) currentId = getStoredId();
  return currentId;
}

/**
 * Returns { userId, setUserId } backed by localStorage.
 * On first visit a random ID is auto-generated.
 */
export function useUserId() {
  const userId = useSyncExternalStore(subscribe, getSnapshot);

  const setUserId = useCallback((id: number) => {
    currentId = id;
    localStorage.setItem(STORAGE_KEY, String(id));
    // Force re-render in same tab by dispatching a storage-like update.
    window.dispatchEvent(
      new StorageEvent("storage", { key: STORAGE_KEY, newValue: String(id) })
    );
  }, []);

  return { userId, setUserId };
}
