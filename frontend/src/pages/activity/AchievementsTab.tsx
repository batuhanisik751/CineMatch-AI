import { useEffect, useState } from "react";
import { getUserAchievements } from "../../api/users";
import { useUserId } from "../../hooks/useUserId";
import type { AchievementResponse } from "../../api/types";

export default function AchievementsTab() {
  const { userId } = useUserId();
  const [data, setData] = useState<AchievementResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!userId) return;
    setLoading(true);
    getUserAchievements(userId)
      .then(setData)
      .catch(() => setError("Failed to load achievements"))
      .finally(() => setLoading(false));
  }, [userId]);

  return (
    <>
      <header className="mb-10">
        <h1 className="text-5xl md:text-6xl font-extrabold font-headline text-on-surface">
          Achievements
        </h1>
        {data && (
          <p className="mt-3 text-on-surface-variant text-lg">
            <span className="text-primary font-bold">{data.unlocked_count}</span>
            {" / "}
            {data.total_count} unlocked
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {data.badges.map((badge) => (
            <div
              key={badge.id}
              className={`glass-card p-6 rounded-2xl transition-all ${
                badge.unlocked
                  ? "bg-primary/10 border border-primary/20"
                  : "bg-surface-container border border-white/5"
              }`}
            >
              <div className="flex items-start gap-4">
                <div
                  className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
                    badge.unlocked
                      ? "bg-primary/20"
                      : "bg-surface-variant/30"
                  }`}
                >
                  <span
                    className={`material-symbols-outlined text-2xl ${
                      badge.unlocked
                        ? "text-primary"
                        : "text-on-surface-variant/40"
                    }`}
                    style={
                      badge.unlocked
                        ? { fontVariationSettings: "'FILL' 1" }
                        : undefined
                    }
                  >
                    {badge.icon}
                  </span>
                </div>

                <div className="flex-1 min-w-0">
                  <h3
                    className={`font-headline font-bold text-sm ${
                      badge.unlocked
                        ? "text-primary"
                        : "text-on-surface-variant/60"
                    }`}
                  >
                    {badge.name}
                  </h3>
                  <p
                    className={`text-xs mt-0.5 ${
                      badge.unlocked
                        ? "text-on-surface-variant"
                        : "text-on-surface-variant/40"
                    }`}
                  >
                    {badge.description}
                  </p>

                  {badge.unlocked && badge.unlocked_detail && (
                    <p className="text-xs text-primary/70 mt-1">
                      {badge.unlocked_detail}
                    </p>
                  )}

                  {!badge.unlocked && (
                    <div className="mt-3">
                      <div className="flex justify-between text-xs text-on-surface-variant/40 mb-1">
                        <span>Progress</span>
                        <span>
                          {badge.progress} / {badge.target}
                        </span>
                      </div>
                      <div className="h-1.5 rounded-full bg-surface-variant/30">
                        <div
                          className="h-full rounded-full bg-primary/40 transition-all"
                          style={{
                            width: `${Math.min(
                              100,
                              (badge.progress / badge.target) * 100
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  )}

                  {badge.unlocked && (
                    <div className="mt-2">
                      <span className="inline-flex items-center gap-1 text-xs text-primary/80 font-medium">
                        <span
                          className="material-symbols-outlined text-sm"
                          style={{ fontVariationSettings: "'FILL' 1" }}
                        >
                          check_circle
                        </span>
                        Unlocked
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
