import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import type { DiaryDay, DiaryResponse } from "../api/types";
import { getUserDiary } from "../api/users";
import BottomNav from "../components/BottomNav";
import ErrorPanel from "../components/ErrorPanel";
import LoadingSpinner from "../components/LoadingSpinner";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";

const MONTH_LABELS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
const DAY_LABELS = ["", "Mon", "", "Wed", "", "Fri", ""];

function getColor(count: number): string {
  if (count === 0) return "bg-white/[0.04]";
  if (count === 1) return "bg-primary/30";
  if (count === 2) return "bg-primary/50";
  if (count === 3) return "bg-primary/70";
  return "bg-primary";
}

interface CalendarCell {
  date: string;
  week: number;
  dow: number;
}

function buildGrid(year: number): { cells: CalendarCell[]; monthCols: { label: string; col: number }[] } {
  const cells: CalendarCell[] = [];
  const monthCols: { label: string; col: number }[] = [];
  const seenMonth = new Set<number>();

  const start = new Date(year, 0, 1);
  const end = new Date(year, 11, 31);
  const startDow = start.getDay(); // 0=Sun

  for (let d = new Date(start); d <= end; d.setDate(d.getDate() + 1)) {
    const dayOfYear = Math.floor(
      (d.getTime() - start.getTime()) / 86_400_000
    );
    const dow = d.getDay();
    const week = Math.floor((dayOfYear + startDow) / 7);

    const month = d.getMonth();
    if (!seenMonth.has(month)) {
      seenMonth.add(month);
      monthCols.push({ label: MONTH_LABELS[month], col: week });
    }

    const iso = `${year}-${String(month + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
    cells.push({ date: iso, week, dow });
  }

  return { cells, monthCols };
}

export default function Diary() {
  const { userId } = useUserId();
  const [year, setYear] = useState(new Date().getFullYear());
  const [diary, setDiary] = useState<DiaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError("");
    setSelectedDate(null);
    getUserDiary(userId, year)
      .then(setDiary)
      .catch((e) => setError(e.detail || e.message))
      .finally(() => setLoading(false));
  }, [userId, year]);

  const dayMap = useMemo(() => {
    const m = new Map<string, DiaryDay>();
    if (diary) {
      for (const day of diary.days) {
        m.set(day.date, day);
      }
    }
    return m;
  }, [diary]);

  const { cells, monthCols } = useMemo(() => buildGrid(year), [year]);
  const totalWeeks = cells.length > 0 ? cells[cells.length - 1].week + 1 : 53;

  const selectedDay = selectedDate ? dayMap.get(selectedDate) : null;

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-24 pb-32 lg:pl-64">
        <div className="max-w-7xl mx-auto px-6 md:px-10">
          {/* Header */}
          <div className="mb-12">
            <h1 className="text-5xl md:text-6xl font-extrabold font-headline tracking-tighter text-on-surface text-glow">
              FILM DIARY
            </h1>
            <p className="text-on-surface-variant mt-3 text-lg">
              Your movie-watching journey at a glance
            </p>
          </div>

          {/* Year navigation */}
          <div className="flex items-center gap-4 mb-8">
            <button
              onClick={() => setYear((y) => y - 1)}
              className="w-10 h-10 rounded-full glass-panel flex items-center justify-center text-on-surface hover:text-primary transition-colors"
            >
              <span className="material-symbols-outlined text-xl">
                chevron_left
              </span>
            </button>
            <span className="text-2xl font-bold font-headline text-on-surface">
              {year}
            </span>
            <button
              onClick={() => setYear((y) => y + 1)}
              disabled={year >= new Date().getFullYear()}
              className="w-10 h-10 rounded-full glass-panel flex items-center justify-center text-on-surface hover:text-primary transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-xl">
                chevron_right
              </span>
            </button>
            {diary && (
              <span className="ml-auto text-on-surface-variant text-sm">
                {diary.total_ratings} rating
                {diary.total_ratings !== 1 ? "s" : ""} this year
              </span>
            )}
          </div>

          {loading && <LoadingSpinner />}
          {error && <ErrorPanel message={error} />}

          {!loading && !error && diary && (
            <>
              {/* Calendar heatmap */}
              <div className="glass-panel rounded-2xl p-6 overflow-x-auto">
                {/* Month labels */}
                <div
                  className="grid gap-[3px] ml-8 mb-1"
                  style={{
                    gridTemplateColumns: `repeat(${totalWeeks}, 14px)`,
                  }}
                >
                  {Array.from({ length: totalWeeks }, (_, w) => {
                    const mc = monthCols.find((m) => m.col === w);
                    return (
                      <span
                        key={w}
                        className="text-[10px] text-on-surface-variant leading-none"
                      >
                        {mc ? mc.label : ""}
                      </span>
                    );
                  })}
                </div>

                {/* Grid with day labels */}
                <div className="flex">
                  {/* Day labels */}
                  <div className="flex flex-col gap-[3px] mr-1 flex-shrink-0">
                    {DAY_LABELS.map((label, i) => (
                      <span
                        key={i}
                        className="text-[10px] text-on-surface-variant h-[14px] flex items-center justify-end w-7"
                      >
                        {label}
                      </span>
                    ))}
                  </div>

                  {/* Heatmap cells */}
                  <div
                    className="grid gap-[3px]"
                    style={{
                      gridTemplateColumns: `repeat(${totalWeeks}, 14px)`,
                      gridTemplateRows: "repeat(7, 14px)",
                    }}
                  >
                    {cells.map((cell) => {
                      const day = dayMap.get(cell.date);
                      const count = day?.count ?? 0;
                      const isSelected = selectedDate === cell.date;
                      return (
                        <button
                          key={cell.date}
                          onClick={() =>
                            setSelectedDate(
                              isSelected ? null : cell.date
                            )
                          }
                          title={`${cell.date}: ${count} rating${count !== 1 ? "s" : ""}`}
                          className={`rounded-sm ${getColor(count)} ${isSelected ? "ring-2 ring-primary" : ""} hover:ring-1 hover:ring-on-surface/30 transition-all cursor-pointer`}
                          style={{
                            gridColumn: cell.week + 1,
                            gridRow: cell.dow + 1,
                          }}
                        />
                      );
                    })}
                  </div>
                </div>

                {/* Legend */}
                <div className="flex items-center gap-2 mt-4 ml-8">
                  <span className="text-[10px] text-on-surface-variant">
                    Less
                  </span>
                  {[0, 1, 2, 3, 4].map((level) => (
                    <div
                      key={level}
                      className={`w-[14px] h-[14px] rounded-sm ${getColor(level)}`}
                    />
                  ))}
                  <span className="text-[10px] text-on-surface-variant">
                    More
                  </span>
                </div>
              </div>

              {/* Selected day detail */}
              {selectedDay && (
                <div className="glass-panel rounded-2xl p-6 mt-6">
                  <h3 className="text-lg font-bold font-headline text-on-surface mb-4">
                    {selectedDate}
                    <span className="ml-2 text-sm font-normal text-on-surface-variant">
                      {selectedDay.count} movie
                      {selectedDay.count !== 1 ? "s" : ""} rated
                    </span>
                  </h3>
                  <div className="space-y-3">
                    {selectedDay.movies.map((movie) => (
                      <Link
                        key={movie.id}
                        to={`/movies/${movie.id}`}
                        className="flex items-center justify-between p-3 rounded-xl hover:bg-white/5 transition-colors"
                      >
                        <span className="text-on-surface font-medium">
                          {movie.title ?? `Movie #${movie.id}`}
                        </span>
                        <span className="flex items-center gap-1 text-primary">
                          <span className="material-symbols-outlined text-base">
                            star
                          </span>
                          <span className="text-sm font-bold">
                            {movie.rating}
                          </span>
                        </span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}

              {/* Empty day message */}
              {selectedDate && !selectedDay && (
                <div className="glass-panel rounded-2xl p-6 mt-6 text-center text-on-surface-variant">
                  No movies rated on {selectedDate}
                </div>
              )}
            </>
          )}
        </div>
      </main>
      <BottomNav />
    </>
  );
}
