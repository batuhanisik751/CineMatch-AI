import { useEffect, useState } from "react";
import { getMovieDNA } from "../api/movies";
import type { MovieDNAResponse } from "../api/types";
import ErrorPanel from "./ErrorPanel";
import LoadingSpinner from "./LoadingSpinner";

const GENRE_COLORS: Record<string, string> = {
  Action: "#ef4444",
  Adventure: "#f97316",
  Animation: "#fbbf24",
  Comedy: "#a3e635",
  Crime: "#6366f1",
  Documentary: "#0ea5e9",
  Drama: "#8b5cf6",
  Family: "#f472b6",
  Fantasy: "#c084fc",
  History: "#a78bfa",
  Horror: "#dc2626",
  Music: "#2dd4bf",
  Mystery: "#818cf8",
  Romance: "#fb7185",
  "Science Fiction": "#22d3ee",
  Thriller: "#facc15",
  "TV Movie": "#94a3b8",
  War: "#78716c",
  Western: "#d97706",
};

function getGenreColor(genre: string): string {
  return GENRE_COLORS[genre] ?? "#64748b";
}

export default function MovieDNA({ movieId }: { movieId: number }) {
  const [dna, setDna] = useState<MovieDNAResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!movieId) return;
    setLoading(true);
    setError("");
    getMovieDNA(movieId)
      .then((data) => setDna(data))
      .catch((e) => setError(e.detail || "Failed to load movie DNA"))
      .finally(() => setLoading(false));
  }, [movieId]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorPanel message={error} />;
  if (!dna) return null;

  const maxGenreWeight = Math.max(...dna.genres.map((g) => g.weight), 0.01);

  return (
    <div className="mt-6 rounded-xl border border-white/10 bg-white/5 p-5">
      <h3 className="mb-4 flex items-center gap-2 text-lg font-semibold text-white">
        <span className="material-symbols-rounded text-xl text-purple-400">
          genetics
        </span>
        Movie DNA
      </h3>

      {/* Decade badge */}
      {dna.decade != null && (
        <div className="mb-4">
          <span className="inline-block rounded-full bg-amber-500/20 px-3 py-1 text-sm font-medium text-amber-300 border border-amber-500/30">
            {dna.decade}s
          </span>
          {dna.director && (
            <span className="ml-2 text-sm text-zinc-400">
              Directed by{" "}
              <span className="text-zinc-200">{dna.director}</span>
            </span>
          )}
        </div>
      )}

      {/* Genre DNA bar */}
      {dna.genres.length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-400">
            Genre DNA
          </p>
          <div className="flex h-4 overflow-hidden rounded-full">
            {dna.genres.map((g) => (
              <div
                key={g.genre}
                className="relative group"
                style={{
                  width: `${(g.weight / maxGenreWeight) * 100}%`,
                  minWidth: "4px",
                  backgroundColor: getGenreColor(g.genre),
                }}
              >
                <div className="pointer-events-none absolute -top-8 left-1/2 -translate-x-1/2 whitespace-nowrap rounded bg-zinc-800 px-2 py-1 text-xs text-white opacity-0 transition-opacity group-hover:opacity-100">
                  {g.genre} ({Math.round(g.weight * 100)}%)
                </div>
              </div>
            ))}
          </div>
          <div className="mt-2 flex flex-wrap gap-2">
            {dna.genres.map((g) => (
              <span
                key={g.genre}
                className="flex items-center gap-1 text-xs text-zinc-300"
              >
                <span
                  className="inline-block h-2 w-2 rounded-full"
                  style={{ backgroundColor: getGenreColor(g.genre) }}
                />
                {g.genre}
                <span className="text-zinc-500">
                  {Math.round(g.weight * 100)}%
                </span>
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Top Keywords */}
      {dna.top_keywords.length > 0 && (
        <div className="mb-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-400">
            Key Themes
          </p>
          <div className="flex flex-wrap gap-2">
            {dna.top_keywords.map((kw) => (
              <span
                key={kw.keyword}
                className="rounded-md border border-white/10 bg-white/5 px-2 py-1 text-zinc-300"
                style={{
                  fontSize: `${Math.max(0.7, 0.7 + kw.weight * 0.3)}rem`,
                }}
              >
                {kw.keyword}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Mood / Vibe Tags */}
      {dna.mood_tags.length > 0 && (
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-zinc-400">
            Vibe
          </p>
          <div className="flex flex-wrap gap-2">
            {dna.mood_tags.map((tag) => (
              <span
                key={tag}
                className="rounded-full border border-purple-500/30 bg-purple-500/10 px-3 py-1 text-sm italic text-purple-300"
              >
                {tag}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
