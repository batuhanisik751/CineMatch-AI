import { Link } from "react-router-dom";
import type { MovieSummary } from "../api/types";

function posterUrl(path: string | null, size = "w300") {
  if (!path) return null;
  return `https://image.tmdb.org/t/p/${size}${path}`;
}

interface Props {
  movie: MovieSummary;
  matchPercent?: number;
  isBookmarked?: boolean;
  onToggleBookmark?: (movieId: number) => void;
}

export default function MovieCard({ movie, matchPercent, isBookmarked, onToggleBookmark }: Props) {
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
      </div>
    </Link>
  );
}
