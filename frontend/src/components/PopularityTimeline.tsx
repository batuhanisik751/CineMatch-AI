import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { getMovieActivity } from "../api/movies";
import type { MovieActivityResponse } from "../api/types";
import LoadingSpinner from "./LoadingSpinner";
import ErrorPanel from "./ErrorPanel";

function formatPeriod(period: string, granularity: string): string {
  if (granularity === "month") {
    const [year, month] = period.split("-");
    const date = new Date(Number(year), Number(month) - 1);
    return date.toLocaleDateString("en-US", { year: "numeric", month: "short" });
  }
  return period;
}

export default function PopularityTimeline({ movieId }: { movieId: number }) {
  const [data, setData] = useState<MovieActivityResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [granularity, setGranularity] = useState<"month" | "week">("month");

  useEffect(() => {
    if (!movieId) return;
    setLoading(true);
    setError("");
    getMovieActivity(movieId, granularity)
      .then((res) => setData(res))
      .catch((e) => setError(e.detail || "Failed to load activity"))
      .finally(() => setLoading(false));
  }, [movieId, granularity]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorPanel message={error} />;
  if (!data || data.timeline.length === 0) return null;

  const chartData = data.timeline.map((p) => ({
    period: formatPeriod(p.period, granularity),
    rating_count: p.rating_count,
    avg_rating: p.avg_rating,
  }));

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-3xl font-headline font-extrabold text-on-surface tracking-tight">
          <span className="material-symbols-outlined text-primary align-middle mr-2 text-3xl">timeline</span>
          Popularity Timeline
        </h3>
        <div className="flex gap-1 bg-surface-container rounded-lg p-1">
          {(["month", "week"] as const).map((g) => (
            <button
              key={g}
              onClick={() => setGranularity(g)}
              className={`px-3 py-1.5 rounded-md text-sm font-semibold transition-all ${
                granularity === g
                  ? "bg-primary text-on-primary shadow-sm"
                  : "text-on-surface-variant hover:bg-surface-container-high"
              }`}
            >
              {g === "month" ? "Monthly" : "Weekly"}
            </button>
          ))}
        </div>
      </div>

      <p className="text-on-surface-variant text-sm mb-4">
        {data.total_ratings.toLocaleString()} total ratings over time
      </p>

      <div className="bg-surface-container rounded-2xl p-6">
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
            <defs>
              <linearGradient id="activityGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="period"
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              interval="preserveStartEnd"
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickLine={false}
              axisLine={false}
              width={40}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "rgba(30,30,46,0.95)",
                border: "1px solid rgba(139,92,246,0.3)",
                borderRadius: "12px",
                color: "#e2e8f0",
                fontSize: 13,
              }}
              formatter={(value, name) => {
                const v = Number(value ?? 0);
                if (name === "rating_count") return [v.toLocaleString(), "Ratings"];
                if (name === "avg_rating") return [v.toFixed(1), "Avg Rating"];
                return [v, String(name ?? "")];
              }}
              labelStyle={{ color: "#94a3b8", fontWeight: 600, marginBottom: 4 }}
            />
            <Area
              type="monotone"
              dataKey="rating_count"
              stroke="#8b5cf6"
              strokeWidth={2}
              fill="url(#activityGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
