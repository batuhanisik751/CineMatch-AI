import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import TopNav from "../components/TopNav";
import Sidebar from "../components/Sidebar";
import BottomNav from "../components/BottomNav";
import { getChallengeProgress } from "../api/challenges";
import { useUserId } from "../hooks/useUserId";
import type { ChallengesProgressResponse } from "../api/types";

export default function Challenges() {
  const { userId } = useUserId();
  const [data, setData] = useState<ChallengesProgressResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    getChallengeProgress(userId)
      .then(setData)
      .catch(() => setError("Failed to load challenges"))
      .finally(() => setLoading(false));
  }, [userId]);

  function statusColor(completed: boolean, progress: number) {
    if (completed) return "primary";
    if (progress > 0) return "tertiary";
    return "on-surface-variant";
  }

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-24 pb-32 lg:pl-64 px-6 max-w-6xl mx-auto">
        <header className="mb-10">
          <h1 className="text-5xl md:text-6xl font-extrabold font-headline text-on-surface">
            Weekly Challenges
          </h1>
          {data && (
            <p className="mt-3 text-on-surface-variant text-lg">
              <span className="text-primary font-bold">
                {data.completed_count}
              </span>
              {" / "}
              {data.total_count} completed &middot;{" "}
              <span className="text-on-surface-variant/60">{data.week}</span>
            </p>
          )}
        </header>

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

        {data && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {data.challenges.map((c) => {
              const color = statusColor(c.completed, c.progress);
              return (
                <div
                  key={c.id}
                  className={`glass-card p-6 rounded-2xl transition-all ${
                    c.completed
                      ? "bg-primary/10 border border-primary/20"
                      : c.progress > 0
                        ? "bg-tertiary/5 border border-tertiary/15"
                        : "bg-surface-container border border-white/5"
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div
                      className={`w-14 h-14 rounded-xl flex items-center justify-center shrink-0 ${
                        c.completed
                          ? "bg-primary/20"
                          : c.progress > 0
                            ? "bg-tertiary/15"
                            : "bg-surface-variant/30"
                      }`}
                    >
                      <span
                        className={`material-symbols-outlined text-3xl text-${color}`}
                        style={
                          c.completed
                            ? { fontVariationSettings: "'FILL' 1" }
                            : undefined
                        }
                      >
                        {c.icon}
                      </span>
                    </div>

                    <div className="flex-1 min-w-0">
                      <h3
                        className={`font-headline font-bold text-base ${
                          c.completed
                            ? "text-primary"
                            : c.progress > 0
                              ? "text-tertiary"
                              : "text-on-surface-variant/60"
                        }`}
                      >
                        {c.title}
                      </h3>
                      <p
                        className={`text-sm mt-1 ${
                          c.completed
                            ? "text-on-surface-variant"
                            : "text-on-surface-variant/50"
                        }`}
                      >
                        {c.description}
                      </p>

                      <div className="mt-4">
                        <div className="flex justify-between text-xs text-on-surface-variant/50 mb-1.5">
                          <span>Progress</span>
                          <span className="font-medium">
                            {c.progress} / {c.target}
                          </span>
                        </div>
                        <div className="h-2 rounded-full bg-surface-variant/30">
                          <div
                            className={`h-full rounded-full transition-all ${
                              c.completed
                                ? "bg-primary"
                                : c.progress > 0
                                  ? "bg-tertiary/60"
                                  : "bg-surface-variant/50"
                            }`}
                            style={{
                              width: `${Math.min(
                                100,
                                (c.progress / c.target) * 100
                              )}%`,
                            }}
                          />
                        </div>
                      </div>

                      {c.completed && (
                        <div className="mt-3">
                          <span className="inline-flex items-center gap-1 text-xs text-primary/80 font-medium">
                            <span
                              className="material-symbols-outlined text-sm"
                              style={{
                                fontVariationSettings: "'FILL' 1",
                              }}
                            >
                              check_circle
                            </span>
                            Completed
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        <div className="mt-8 text-center">
          <Link
            to="/profile"
            className="text-sm text-on-surface-variant hover:text-primary transition-colors"
          >
            Back to Profile
          </Link>
        </div>
      </main>
      <BottomNav />
    </>
  );
}
