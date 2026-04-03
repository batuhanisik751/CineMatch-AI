import { useEffect, useMemo, useState } from "react";
import { getUserBingo } from "../../api/bingo";
import { useUserId } from "../../hooks/useUserId";
import type { BingoCardResponse } from "../../api/types";

function formatSeed(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
}

function formatMonthLabel(seed: string): string {
  const [year, month] = seed.split("-");
  const d = new Date(Number(year), Number(month) - 1);
  return d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
}

function shiftMonth(seed: string, delta: number): string {
  const [year, month] = seed.split("-").map(Number);
  const d = new Date(year, month - 1 + delta);
  return formatSeed(d);
}

export default function BingoTab() {
  const { userId } = useUserId();
  const [seed, setSeed] = useState(() => formatSeed(new Date()));
  const [data, setData] = useState<BingoCardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    setError("");
    getUserBingo(userId, seed)
      .then(setData)
      .catch(() => setError("Failed to load bingo card"))
      .finally(() => setLoading(false));
  }, [userId, seed]);

  // Build a set of indices that belong to completed lines for glow effect
  const glowIndices = useMemo(() => {
    if (!data) return new Set<number>();
    const s = new Set<number>();
    for (const line of data.completed_lines) {
      for (const i of line) s.add(i);
    }
    return s;
  }, [data]);

  return (
    <div className="max-w-3xl mx-auto">
      <header className="mb-10">
        <h1 className="text-5xl md:text-6xl font-extrabold font-headline text-on-surface">
          Movie Bingo
        </h1>
        <p className="mt-3 text-on-surface-variant text-lg">
          Complete categories by rating matching movies
        </p>
      </header>

      {/* Month selector */}
      <div className="flex items-center justify-center gap-4 mb-8">
        <button
          onClick={() => setSeed(shiftMonth(seed, -1))}
          className="w-10 h-10 rounded-full bg-surface-container border border-white/5 flex items-center justify-center hover:bg-surface-variant/30 transition-colors"
        >
          <span className="material-symbols-outlined text-on-surface-variant">
            chevron_left
          </span>
        </button>
        <span className="text-on-surface font-headline font-bold text-xl min-w-[200px] text-center">
          {formatMonthLabel(seed)}
        </span>
        <button
          onClick={() => setSeed(shiftMonth(seed, 1))}
          className="w-10 h-10 rounded-full bg-surface-container border border-white/5 flex items-center justify-center hover:bg-surface-variant/30 transition-colors"
        >
          <span className="material-symbols-outlined text-on-surface-variant">
            chevron_right
          </span>
        </button>
      </div>

      {/* Stats bar */}
      {data && (
        <div className="flex justify-center gap-8 mb-8 text-sm">
          <div className="text-center">
            <span className="text-primary font-bold text-2xl">
              {data.total_completed}
            </span>
            <span className="text-on-surface-variant"> / 25 cells</span>
          </div>
          <div className="text-center">
            <span className="text-tertiary font-bold text-2xl">
              {data.bingo_count}
            </span>
            <span className="text-on-surface-variant">
              {" "}
              bingo{data.bingo_count !== 1 ? "s" : ""}
            </span>
          </div>
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-20">
          <span className="material-symbols-outlined text-4xl text-on-surface-variant animate-spin">
            progress_activity
          </span>
        </div>
      )}

      {error && (
        <div className="glass-card p-6 text-error text-center">{error}</div>
      )}

      {/* 5x5 Bingo Grid */}
      {data && (
        <div className="grid grid-cols-5 gap-2">
          {data.cells.map((cell) => {
            const isFree = cell.template === "free";
            const hasGlow = glowIndices.has(cell.index);

            return (
              <div
                key={cell.index}
                className={`relative aspect-square rounded-xl flex flex-col items-center justify-center p-1.5 text-center transition-all border ${
                  isFree
                    ? "bg-tertiary/20 border-tertiary/30"
                    : cell.completed
                      ? hasGlow
                        ? "bg-primary/20 border-primary/40 shadow-[0_0_12px_rgba(255,228,175,0.3)]"
                        : "bg-primary/15 border-primary/25"
                      : "bg-surface-container border-white/5"
                }`}
              >
                {/* Completed checkmark */}
                {cell.completed && !isFree && (
                  <span
                    className="material-symbols-outlined text-primary text-base absolute top-1 right-1"
                    style={{ fontVariationSettings: "'FILL' 1" }}
                  >
                    check_circle
                  </span>
                )}

                {isFree ? (
                  <>
                    <span
                      className="material-symbols-outlined text-tertiary text-2xl md:text-3xl"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      star
                    </span>
                    <span className="text-tertiary font-bold text-xs mt-1">
                      FREE
                    </span>
                  </>
                ) : (
                  <span
                    className={`text-[10px] md:text-xs leading-tight font-medium ${
                      cell.completed
                        ? "text-primary"
                        : "text-on-surface-variant/60"
                    }`}
                  >
                    {cell.label}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
