import { useRef, useState } from "react";
import { semanticSearchMovies } from "../api/movies";
import { getMoodRecommendations } from "../api/recommendations";
import type { MovieSummary } from "../api/types";
import BottomNav from "../components/BottomNav";
import MoodCarousel from "../components/MoodCarousel";
import MoodPills from "../components/MoodPills";
import Sidebar from "../components/Sidebar";
import TopNav from "../components/TopNav";
import { MOOD_PRESETS, type MoodPreset } from "../constants/moods";
import { useDismissed } from "../hooks/useDismissed";
import { useRated } from "../hooks/useRated";
import { useUserId } from "../hooks/useUserId";
import { useWatchlist } from "../hooks/useWatchlist";

interface MoodResult {
  query: string;
  movies: MovieSummary[];
  loading: boolean;
  isPersonalized: boolean;
}

export default function Moods() {
  const { userId } = useUserId();
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const [activeMoods, setActiveMoods] = useState<Map<string, MoodResult>>(new Map());
  const abortControllers = useRef<Map<string, AbortController>>(new Map());
  const moodFallback = useRef(false);
  const [customVibe, setCustomVibe] = useState("");

  const activeMoodLabels = new Set(activeMoods.keys());
  const loadingMoodLabels = new Set(
    [...activeMoods.entries()].filter(([, v]) => v.loading).map(([k]) => k)
  );

  const fetchMood = (query: string, label: string) => {
    // Abort any existing request for this label
    abortControllers.current.get(label)?.abort();
    const controller = new AbortController();
    abortControllers.current.set(label, controller);

    setActiveMoods((prev) => {
      const next = new Map(prev);
      next.set(label, { query, movies: [], loading: true, isPersonalized: false });
      return next;
    });

    const applyResults = (movies: MovieSummary[], personalized: boolean) => {
      if (controller.signal.aborted) return;
      setActiveMoods((prev) => {
        const next = new Map(prev);
        const entry = next.get(label);
        if (entry) {
          next.set(label, { ...entry, movies, loading: false, isPersonalized: personalized });
        }
        return next;
      });
      const ids = movies.map((m) => m.id);
      refreshForMovieIds(ids);
      refreshDismissedForMovieIds(ids);
      refreshRatingsForMovieIds(ids);
    };

    const fallbackToSemantic = () =>
      semanticSearchMovies(query, 20).then((data) =>
        applyResults(data.results.map((r) => r.movie), false)
      );

    const request = !moodFallback.current && userId
      ? getMoodRecommendations({ mood: query, user_id: userId })
          .then((data) => applyResults(data.results.map((r) => r.movie), data.is_personalized))
          .catch(() => {
            moodFallback.current = true;
            return fallbackToSemantic();
          })
      : fallbackToSemantic();

    request
      .catch(() => {
        if (!controller.signal.aborted) {
          setActiveMoods((prev) => {
            const next = new Map(prev);
            const entry = next.get(label);
            if (entry) {
              next.set(label, { ...entry, movies: [], loading: false });
            }
            return next;
          });
        }
      });
  };

  const removeMood = (label: string) => {
    abortControllers.current.get(label)?.abort();
    abortControllers.current.delete(label);
    setActiveMoods((prev) => {
      const next = new Map(prev);
      next.delete(label);
      return next;
    });
  };

  const handleMoodSelect = (mood: MoodPreset) => {
    if (activeMoods.has(mood.label)) {
      removeMood(mood.label);
    } else {
      fetchMood(mood.query, mood.label);
    }
  };

  const handleCustomVibe = (e: React.FormEvent) => {
    e.preventDefault();
    const vibe = customVibe.trim();
    if (!vibe) return;
    fetchMood(vibe, vibe);
    setCustomVibe("");
  };

  // Preserve insertion order from Map
  const moodEntries = [...activeMoods.entries()];

  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <header className="mb-10 text-center">
            <h1 className="font-headline font-extrabold text-on-surface tracking-tight mb-2 text-3xl md:text-5xl">
              Moods
            </h1>
            <p className="text-on-surface-variant font-label text-sm uppercase tracking-[0.2em]">
              Discover movies by vibe — select moods to explore themed collections
            </p>
          </header>

          <MoodPills
            onSelect={handleMoodSelect}
            activeMoods={activeMoodLabels}
            loading={false}
            loadingMoods={loadingMoodLabels}
          />

          <form
            onSubmit={handleCustomVibe}
            className="w-full max-w-xl mx-auto mt-8 flex gap-3"
          >
            <input
              value={customVibe}
              onChange={(e) => setCustomVibe(e.target.value)}
              className="flex-1 h-12 px-5 bg-surface-container-lowest border border-outline-variant/20 rounded-full text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint transition-all duration-300 font-body text-sm"
              placeholder="Or describe your own vibe..."
              type="text"
              maxLength={200}
            />
            <button
              type="submit"
              disabled={!customVibe.trim()}
              className="h-12 px-6 bg-primary text-on-primary rounded-full font-label font-bold text-sm tracking-wide hover:shadow-[0_0_20px_rgba(255,193,7,0.3)] transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Discover
            </button>
          </form>

          {moodEntries.length === 0 && (
            <div className="text-center py-20">
              <span className="material-symbols-outlined text-6xl text-outline/30 mb-4 block">
                mood
              </span>
              <p className="text-on-surface-variant text-lg">
                Pick a mood above to start discovering movies
              </p>
            </div>
          )}

          <div className="mt-12 space-y-4">
            {moodEntries.map(([label, result]) => {
              const presetMatch = MOOD_PRESETS.find((p) => p.label === label);
              return (
                <div key={label} className="relative">
                  <button
                    onClick={() => removeMood(label)}
                    className="absolute top-2 right-2 z-10 w-8 h-8 flex items-center justify-center rounded-full bg-surface-container-highest/80 text-on-surface-variant hover:bg-error hover:text-on-error transition-all duration-200"
                    title="Dismiss"
                  >
                    <span className="material-symbols-outlined text-lg">close</span>
                  </button>
                  <MoodCarousel
                    mood={presetMatch ? label : `"${label}"`}
                    movies={result.movies}
                    loading={result.loading}
                    isPersonalized={result.isPersonalized}
                    isBookmarked={isInWatchlist}
                    onToggleBookmark={toggle}
                    isDismissed={isDismissed}
                    onDismiss={toggleDismiss}
                    getRating={getRating}
                  />
                </div>
              );
            })}
          </div>
        </div>
      </main>
      <BottomNav />
    </>
  );
}
