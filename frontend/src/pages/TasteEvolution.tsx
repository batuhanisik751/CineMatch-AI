import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { TasteEvolutionResponse } from "../api/types";
import { getUserTasteEvolution } from "../api/users";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";

const GRANULARITY_OPTIONS = [
  { value: "month", label: "Monthly" },
  { value: "quarter", label: "Quarterly" },
  { value: "year", label: "Yearly" },
];

const GENRE_COLORS = [
  "#FFC107", "#ef4444", "#3b82f6", "#22c55e", "#a855f7",
  "#f97316", "#06b6d4", "#ec4899", "#14b8a6", "#eab308",
  "#8b5cf6", "#f43f5e", "#0ea5e9", "#84cc16", "#d946ef",
  "#fb923c", "#2dd4bf", "#e879f9", "#fbbf24", "#34d399",
];

export default function TasteEvolution() {
  const { userId } = useUserId();
  const [granularity, setGranularity] = useState("quarter");
  const [data, setData] = useState<TasteEvolutionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setLoading(true);
    setError("");
    getUserTasteEvolution(userId, granularity)
      .then(setData)
      .catch((e) => setError(e.message || "Failed to load taste evolution"))
      .finally(() => setLoading(false));
  }, [userId, granularity]);

  // Transform data for Recharts: [{period, Action: 40, Drama: 30, ...}]
  const { chartData, allGenres } = useMemo(() => {
    if (!data || data.periods.length === 0) return { chartData: [], allGenres: [] };

    // Collect all genres and sort by total percentage across all periods
    const genreTotals: Record<string, number> = {};
    for (const p of data.periods) {
      for (const [genre, pct] of Object.entries(p.genres)) {
        genreTotals[genre] = (genreTotals[genre] || 0) + pct;
      }
    }
    const sorted = Object.entries(genreTotals)
      .sort((a, b) => b[1] - a[1])
      .map(([g]) => g);

    const rows = data.periods.map((p) => {
      const row: Record<string, string | number> = { period: p.period };
      for (const genre of sorted) {
        row[genre] = p.genres[genre] || 0;
      }
      return row;
    });

    return { chartData: rows, allGenres: sorted };
  }, [data]);

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <header className="mb-10">
            <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
              Taste Evolution
            </h1>
            <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
              How your genre preferences have shifted over time
            </p>
          </header>

          {/* Granularity Toggle */}
          <div className="mb-10">
            <span className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-2 block">
              Time Period
            </span>
            <div className="flex gap-2">
              {GRANULARITY_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setGranularity(opt.value)}
                  className={`px-4 py-2 rounded-full text-xs font-bold uppercase tracking-widest transition-all ${
                    granularity === opt.value
                      ? "bg-primary-container text-on-primary-container shadow-md"
                      : "bg-surface-container-highest text-on-surface-variant hover:bg-surface-container-high"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {loading && <LoadingSpinner />}
          {error && <ErrorPanel message={error} />}

          {!loading && !error && chartData.length === 0 && (
            <p className="text-on-surface-variant text-center py-20">
              No rating history yet. Start rating movies to see your taste evolve!
            </p>
          )}

          {!loading && !error && chartData.length > 0 && (
            <>
              {/* Stacked Area Chart */}
              <div className="rounded-xl bg-surface-container-low p-6 mb-8">
                <ResponsiveContainer width="100%" height={420}>
                  <AreaChart data={chartData} stackOffset="expand">
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis
                      dataKey="period"
                      tick={{ fill: "#a8a29e", fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      tickFormatter={(v: number) => `${Math.round(v * 100)}%`}
                      tick={{ fill: "#a8a29e", fontSize: 11 }}
                      tickLine={false}
                      axisLine={false}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#1c1b1f",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 12,
                        fontSize: 12,
                      }}
                      formatter={(value) => `${(Number(value) * 100).toFixed(1)}%`}
                      labelStyle={{ color: "#e6e1e5" }}
                    />
                    {allGenres.map((genre, i) => (
                      <Area
                        key={genre}
                        type="monotone"
                        dataKey={genre}
                        stackId="1"
                        fill={GENRE_COLORS[i % GENRE_COLORS.length]}
                        stroke={GENRE_COLORS[i % GENRE_COLORS.length]}
                        fillOpacity={0.8}
                      />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              {/* Genre Legend */}
              <div className="flex flex-wrap gap-3">
                {allGenres.map((genre, i) => (
                  <div key={genre} className="flex items-center gap-2 text-sm text-on-surface-variant">
                    <span
                      className="w-3 h-3 rounded-full inline-block"
                      style={{ backgroundColor: GENRE_COLORS[i % GENRE_COLORS.length] }}
                    />
                    {genre}
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </main>
      <BottomNav />
    </>
  );
}
