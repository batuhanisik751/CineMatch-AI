import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getOnboardingMovies, getOnboardingStatus } from "../api/onboarding";
import { addRating } from "../api/ratings";
import type { MovieSummary } from "../api/types";
import StarRating from "../components/StarRating";
import { useRated } from "../hooks/useRated";
import { useUserId } from "../hooks/useUserId";

function posterUrl(path: string | null) {
  if (!path) return null;
  return `https://image.tmdb.org/t/p/w300${path}`;
}

export default function Onboarding() {
  const navigate = useNavigate();
  const { userId } = useUserId();
  const { setLocalRating } = useRated();

  const [movies, setMovies] = useState<MovieSummary[]>([]);
  const [ratings, setRatings] = useState<Map<number, number>>(new Map());
  const [skipped, setSkipped] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [threshold, setThreshold] = useState(10);
  const [submitting, setSubmitting] = useState<number | null>(null);

  useEffect(() => {
    Promise.all([
      getOnboardingMovies(userId, 20),
      getOnboardingStatus(userId),
    ])
      .then(([moviesResp, statusResp]) => {
        setMovies(moviesResp.movies);
        setThreshold(statusResp.threshold);
        if (statusResp.completed) {
          navigate("/", { replace: true });
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [userId, navigate]);

  const ratedCount = ratings.size;
  const progressPct = Math.min((ratedCount / threshold) * 100, 100);
  const canContinue = ratedCount >= threshold;

  const handleRate = useCallback(
    async (movieId: number, rating: number) => {
      setSubmitting(movieId);
      setRatings((prev) => new Map(prev).set(movieId, rating));
      setLocalRating(movieId, rating);
      try {
        await addRating(userId, movieId, rating);
      } catch {
        // Optimistic — rating is stored locally even if API fails
      } finally {
        setSubmitting(null);
      }
    },
    [userId, setLocalRating]
  );

  const handleSkip = useCallback((movieId: number) => {
    setSkipped((prev) => {
      const next = new Set(prev);
      if (next.has(movieId)) {
        next.delete(movieId);
      } else {
        next.add(movieId);
      }
      return next;
    });
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-surface flex items-center justify-center">
        <div className="animate-pulse text-on-surface-variant text-lg">
          Loading movies...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-surface">
      {/* Header */}
      <div className="sticky top-0 z-20 bg-surface/80 backdrop-blur-xl border-b border-outline-variant">
        <div className="max-w-6xl mx-auto px-4 py-6">
          <h1 className="text-3xl font-headline font-bold text-on-surface">
            Welcome to CineMatch
          </h1>
          <p className="text-on-surface-variant mt-1">
            Rate movies you've seen to get personalized recommendations
          </p>

          {/* Progress bar */}
          <div className="mt-4">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-sm font-label text-on-surface-variant">
                {ratedCount} of {threshold} rated
              </span>
              {canContinue && (
                <span className="text-sm font-label text-primary font-bold">
                  Ready!
                </span>
              )}
            </div>
            <div className="h-2 rounded-full bg-surface-container-highest overflow-hidden">
              <div
                className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>

          {/* Continue button */}
          {canContinue && (
            <button
              onClick={() => navigate("/")}
              className="mt-4 px-6 py-2.5 bg-primary text-on-primary font-bold rounded-full hover:bg-primary/90 transition-colors"
            >
              Continue to Recommendations
            </button>
          )}
        </div>
      </div>

      {/* Movie grid */}
      <div className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
          {movies.map((movie) => {
            const poster = posterUrl(movie.poster_path);
            const year = movie.release_date
              ? new Date(movie.release_date).getFullYear()
              : null;
            const userRating = ratings.get(movie.id);
            const isSkipped = skipped.has(movie.id);
            const isSubmitting = submitting === movie.id;

            return (
              <div
                key={movie.id}
                className={`relative flex flex-col bg-surface-container-low rounded-xl overflow-hidden transition-all duration-300 ${
                  isSkipped ? "opacity-40" : ""
                } ${userRating ? "ring-2 ring-primary" : ""}`}
              >
                {/* Rated overlay */}
                {userRating && (
                  <div className="absolute top-3 right-3 z-10 bg-primary text-on-primary text-xs font-black px-2 py-1 rounded-full flex items-center gap-1">
                    <span
                      className="material-symbols-outlined text-[14px]"
                      style={{ fontVariationSettings: "'FILL' 1" }}
                    >
                      star
                    </span>
                    {userRating}/10
                  </div>
                )}

                {/* Poster */}
                <div className="aspect-[2/3] overflow-hidden">
                  {poster ? (
                    <img
                      src={poster}
                      alt={movie.title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-surface-container flex items-center justify-center">
                      <span className="material-symbols-outlined text-5xl text-outline">
                        movie
                      </span>
                    </div>
                  )}
                </div>

                {/* Info */}
                <div className="p-4 flex flex-col gap-2 flex-1">
                  <div>
                    {year && (
                      <p className="text-xs font-label text-on-surface-variant">
                        {year}
                      </p>
                    )}
                    <h3 className="text-sm font-headline font-bold text-on-surface leading-tight">
                      {movie.title}
                    </h3>
                  </div>

                  <div className="flex flex-wrap gap-1">
                    {movie.genres.slice(0, 2).map((g) => (
                      <span
                        key={g}
                        className="text-[9px] font-bold uppercase tracking-widest px-1.5 py-0.5 bg-surface-container-highest text-on-surface-variant rounded"
                      >
                        {g}
                      </span>
                    ))}
                  </div>

                  {/* Rating */}
                  <div className="mt-auto pt-2">
                    {!isSkipped && (
                      <StarRating
                        value={userRating ?? 0}
                        onChange={(val) => handleRate(movie.id, val)}
                        size="text-lg"
                      />
                    )}
                  </div>

                  {/* Skip button */}
                  <button
                    onClick={() => handleSkip(movie.id)}
                    disabled={isSubmitting}
                    className="text-xs text-on-surface-variant hover:text-on-surface transition-colors py-1"
                  >
                    {isSkipped ? "Undo skip" : "Haven't seen it"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
