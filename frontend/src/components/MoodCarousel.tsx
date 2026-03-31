import type { MovieSummary } from "../api/types";
import MovieCard from "./MovieCard";

interface Props {
  mood: string;
  movies: MovieSummary[];
  loading: boolean;
  isPersonalized?: boolean;
  isBookmarked?: (id: number) => boolean;
  onToggleBookmark?: (id: number) => void;
  isDismissed?: (id: number) => boolean;
  onDismiss?: (id: number) => void;
  getRating?: (id: number) => number | null;
}

export default function MoodCarousel({
  mood,
  movies,
  loading,
  isPersonalized,
  isBookmarked,
  onToggleBookmark,
  isDismissed,
  onDismiss,
  getRating,
}: Props) {
  if (!loading && movies.length === 0) return null;

  return (
    <section className="max-w-7xl mx-auto px-6 pb-12">
      <div className="flex items-center gap-3 mb-4">
        <h3 className="font-headline font-bold text-xl text-on-surface">
          For your <span className="text-primary">{mood}</span> mood
        </h3>
        {isPersonalized && (
          <span className="text-[10px] font-bold uppercase tracking-widest px-2 py-1 bg-primary-container text-on-primary-container rounded">
            Personalized
          </span>
        )}
      </div>
      {loading ? (
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
          {Array.from({ length: 6 }).map((_, i) => (
            <div
              key={i}
              className="flex-shrink-0 w-44 aspect-[2/3] bg-surface-container-low rounded-xl animate-pulse"
            />
          ))}
        </div>
      ) : (
        <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
          {movies.map((m) => (
            <div key={m.id} className="flex-shrink-0 w-44">
              <MovieCard
                movie={m}
                isBookmarked={isBookmarked?.(m.id)}
                onToggleBookmark={onToggleBookmark}
                isDismissed={isDismissed?.(m.id)}
                onDismiss={onDismiss}
                userRating={getRating?.(m.id)}
              />
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
