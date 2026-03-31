import { Link } from "react-router-dom";
import type { MovieSummary, ScoreBreakdown } from "../api/types";

function posterUrl(path: string | null, size = "w300") {
  if (!path) return null;
  return `https://image.tmdb.org/t/p/${size}${path}`;
}

interface Props {
  movie: MovieSummary;
  matchPercent?: number;
  isBookmarked?: boolean;
  onToggleBookmark?: (movieId: number) => void;
  isDismissed?: boolean;
  onDismiss?: (movieId: number) => void;
  becauseYouLiked?: string | null;
  featureExplanations?: string[];
  scoreBreakdown?: ScoreBreakdown | null;
}

export default function MovieCard({ movie, matchPercent, isBookmarked, onToggleBookmark, isDismissed, onDismiss, becauseYouLiked, featureExplanations, scoreBreakdown }: Props) {
  const year = movie.release_date ? new Date(movie.release_date).getFullYear() : null;
  const poster = posterUrl(movie.poster_path);

  return (
    <Link
      to={`/movies/${movie.id}`}
      className="group relative flex flex-col bg-surface-container-low rounded-xl overflow-hidden transition-all duration-300 glow-hover cursor-pointer"
    >
      <div className="aspect-[2/3] overflow-hidden relative">
        {poster ? (
          <img
            src={poster}
            alt={movie.title}
            className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700"
          />
        ) : (
          <div className="w-full h-full bg-surface-container flex items-center justify-center">
            <span className="material-symbols-outlined text-5xl text-outline">movie</span>
          </div>
        )}
        {onToggleBookmark && (
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onToggleBookmark(movie.id);
            }}
            className="absolute top-4 left-4 bg-[#131314]/60 backdrop-blur-md p-1.5 rounded border border-white/10 hover:bg-[#131314]/80 transition-colors z-10"
          >
            <span
              className="material-symbols-outlined text-[18px] text-primary"
              style={isBookmarked ? { fontVariationSettings: "'FILL' 1" } : undefined}
            >
              bookmark
            </span>
          </button>
        )}
        <div className="absolute top-4 right-4 bg-[#131314]/60 backdrop-blur-md px-2 py-1 rounded flex items-center gap-1 border border-white/10">
          <span
            className="material-symbols-outlined text-[14px] text-primary-fixed-dim"
            style={{ fontVariationSettings: "'FILL' 1" }}
          >
            star
          </span>
          <span className="text-xs font-bold text-primary">
            {movie.vote_average.toFixed(1)}
          </span>
        </div>
        {matchPercent != null && (
          <div className="absolute bottom-4 left-4">
            <div className="bg-primary-container text-on-primary-container text-[10px] font-black px-2 py-1 rounded-sm tracking-tighter uppercase">
              {matchPercent}% Match
            </div>
          </div>
        )}
        {onDismiss && (
          <button
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              onDismiss(movie.id);
            }}
            className="absolute bottom-4 right-4 bg-[#131314]/60 backdrop-blur-md p-1.5 rounded border border-white/10 hover:bg-error/60 transition-colors z-10"
            title={isDismissed ? "Undo Not Interested" : "Not Interested"}
          >
            <span
              className={`material-symbols-outlined text-[18px] ${isDismissed ? "text-error" : "text-outline"}`}
              style={isDismissed ? { fontVariationSettings: "'FILL' 1" } : undefined}
            >
              visibility_off
            </span>
          </button>
        )}
      </div>
      <div className="p-6 flex flex-col gap-4">
        <div>
          {year && (
            <p className="text-xs font-label text-on-surface-variant mb-1">{year}</p>
          )}
          <h3 className="text-xl font-headline font-bold text-on-surface leading-tight group-hover:text-primary transition-colors">
            {movie.title}
          </h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {movie.genres.slice(0, 3).map((g) => (
            <span
              key={g}
              className="text-[10px] font-bold uppercase tracking-widest px-2 py-1 bg-surface-container-highest text-on-surface-variant rounded"
            >
              {g}
            </span>
          ))}
        </div>
        {(becauseYouLiked || (featureExplanations && featureExplanations.length > 0) || scoreBreakdown) && (
          <div className="flex flex-col gap-2 mt-1">
            {becauseYouLiked && (
              <div className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px] text-primary-fixed-dim">favorite</span>
                <span className="text-[11px] text-on-surface-variant leading-tight">
                  Because you liked <span className="text-on-surface font-semibold">{becauseYouLiked}</span>
                </span>
              </div>
            )}
            {featureExplanations && featureExplanations.slice(0, 2).map((exp, i) => (
              <div key={i} className="flex items-center gap-1.5">
                <span className="material-symbols-outlined text-[14px] text-primary-fixed-dim">info</span>
                <span className="text-[11px] text-on-surface-variant leading-tight">{exp}</span>
              </div>
            ))}
            {scoreBreakdown && matchPercent != null && matchPercent > 0 && (() => {
              const contentContrib = scoreBreakdown.alpha * scoreBreakdown.content_score;
              const collabContrib = (1 - scoreBreakdown.alpha) * scoreBreakdown.collab_score;
              const total = contentContrib + collabContrib;
              const contentPct = total > 0 ? Math.round((contentContrib / total) * 100) : 50;
              return (
                <div className="mt-1">
                  <div className="flex h-1.5 rounded-full overflow-hidden bg-surface-container-highest">
                    <div className="bg-primary-container" style={{ width: `${contentPct}%` }} />
                    <div className="bg-tertiary-container" style={{ width: `${100 - contentPct}%` }} />
                  </div>
                  <div className="flex justify-between mt-1">
                    <span className="text-[9px] text-on-surface-variant">{contentPct}% taste</span>
                    <span className="text-[9px] text-on-surface-variant">{100 - contentPct}% similar users</span>
                  </div>
                </div>
              );
            })()}
          </div>
        )}
      </div>
    </Link>
  );
}
