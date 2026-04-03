import { useEffect, useState } from "react";

interface ToastMessage {
  id: number;
  message: string;
  retryAfter: number;
}

let nextId = 0;

export default function Toast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    function handleRateLimited(e: Event) {
      const { message, retryAfter } = (e as CustomEvent).detail;
      const id = nextId++;
      setToasts((prev) => [...prev, { id, message, retryAfter }]);

      setTimeout(() => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
      }, Math.max(retryAfter * 1000, 4000));
    }

    window.addEventListener("rate-limited", handleRateLimited);
    return () => window.removeEventListener("rate-limited", handleRateLimited);
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className="glass-panel border-amber-500/40 bg-amber-900/30 px-4 py-3 rounded-lg shadow-lg max-w-sm animate-fade-in flex items-start gap-3"
        >
          <span className="text-amber-400 text-lg leading-none mt-0.5">⚠</span>
          <div>
            <p className="text-amber-200 text-sm font-medium">
              Too many requests
            </p>
            <p className="text-amber-300/70 text-xs mt-1">
              Please wait {toast.retryAfter} seconds before trying again.
            </p>
          </div>
          <button
            onClick={() =>
              setToasts((prev) => prev.filter((t) => t.id !== toast.id))
            }
            className="text-amber-400/60 hover:text-amber-300 ml-auto text-sm leading-none"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  );
}
