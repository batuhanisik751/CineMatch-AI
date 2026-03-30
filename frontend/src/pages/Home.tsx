import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { discoverMovies, semanticSearchMovies } from "../api/movies";
import { getMoodRecommendations } from "../api/recommendations";
import type { MovieSummary } from "../api/types";
import BottomNav from "../components/BottomNav";
import MoodCarousel from "../components/MoodCarousel";
import MoodPills from "../components/MoodPills";
import MovieCard from "../components/MovieCard";
import TopNav from "../components/TopNav";
import type { MoodPreset } from "../constants/moods";
import { useUserId } from "../hooks/useUserId";
import { useWatchlist } from "../hooks/useWatchlist";

export default function Home() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const { userId } = useUserId();
  const [strategy, setStrategy] = useState("hybrid");
  const [popular, setPopular] = useState<MovieSummary[]>([]);
  const [topRated, setTopRated] = useState<MovieSummary[]>([]);
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();

  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [moodMovies, setMoodMovies] = useState<MovieSummary[]>([]);
  const [moodLoading, setMoodLoading] = useState(false);
  const [moodPersonalized, setMoodPersonalized] = useState(false);
  const [customVibe, setCustomVibe] = useState("");
  const moodAbort = useRef<AbortController | null>(null);
  const moodFallback = useRef(false);

  useEffect(() => {
    discoverMovies({ sort_by: "popularity", limit: 8 })
      .then((data) => {
        setPopular(data.results);
        refreshForMovieIds(data.results.map((m) => m.id));
      })
      .catch(() => {});
    discoverMovies({ sort_by: "vote_average", limit: 8 })
      .then((data) => {
        setTopRated(data.results);
        refreshForMovieIds(data.results.map((m) => m.id));
      })
      .catch(() => {});
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) navigate(`/discover?q=${encodeURIComponent(query.trim())}`);
  };

  const handleRecs = (e: React.FormEvent) => {
    e.preventDefault();
    navigate(`/recommendations?user=${userId}&strategy=${strategy}`);
  };

  const fetchMoodMovies = (moodQuery: string, label: string) => {
    moodAbort.current?.abort();
    const controller = new AbortController();
    moodAbort.current = controller;
    setSelectedMood(label);
    setMoodLoading(true);
    setMoodPersonalized(false);

    const applyResults = (movies: MovieSummary[], personalized: boolean) => {
      if (controller.signal.aborted) return;
      setMoodMovies(movies);
      setMoodPersonalized(personalized);
      refreshForMovieIds(movies.map((m) => m.id));
    };

    const fallbackToSemantic = () =>
      semanticSearchMovies(moodQuery, 20).then((data) =>
        applyResults(data.results.map((r) => r.movie), false)
      );

    const request = !moodFallback.current && userId
      ? getMoodRecommendations({ mood: moodQuery, user_id: userId })
          .then((data) => applyResults(data.results.map((r) => r.movie), data.is_personalized))
          .catch(() => {
            moodFallback.current = true;
            return fallbackToSemantic();
          })
      : fallbackToSemantic();

    request
      .catch(() => {
        if (!controller.signal.aborted) setMoodMovies([]);
      })
      .finally(() => {
        if (!controller.signal.aborted) setMoodLoading(false);
      });
  };

  const handleMoodSelect = (mood: MoodPreset) => {
    if (selectedMood === mood.label) {
      setSelectedMood(null);
      setMoodMovies([]);
      setMoodPersonalized(false);
      return;
    }
    fetchMoodMovies(mood.query, mood.label);
  };

  const handleCustomVibe = (e: React.FormEvent) => {
    e.preventDefault();
    const vibe = customVibe.trim();
    if (!vibe) return;
    fetchMoodMovies(vibe, vibe);
  };

  return (
    <>
      <TopNav />
      <main className="pt-20">
        {/* Hero Section */}
        <section className="relative h-[870px] flex flex-col items-center justify-center px-6 overflow-hidden">
          <div className="absolute inset-0 z-0">
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/60 to-background" />
            <div className="w-full h-full bg-surface-container-lowest opacity-30" />
          </div>
          <div className="relative z-10 text-center max-w-4xl space-y-8">
            <h1 className="font-headline text-6xl md:text-8xl font-extrabold tracking-tighter text-on-surface">
              CineMatch-AI
            </h1>
            <p className="font-headline text-xl md:text-2xl text-on-surface-variant font-medium tracking-tight">
              Discover your next favorite movie
            </p>
            {/* Search Bar */}
            <form
              onSubmit={handleSearch}
              className="w-full max-w-2xl mx-auto mt-12 relative group"
            >
              <div className="absolute inset-y-0 left-6 flex items-center pointer-events-none">
                <span className="material-symbols-outlined text-outline">search</span>
              </div>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full h-16 pl-16 pr-6 bg-surface-container-lowest border-none rounded-xl text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint shadow-2xl transition-all duration-300 font-body text-lg"
                placeholder="Search for titles, directors, or genres..."
                type="text"
              />
            </form>
            <MoodPills
              onSelect={handleMoodSelect}
              activeMood={selectedMood}
              loading={moodLoading}
            />
            <form
              onSubmit={handleCustomVibe}
              className="w-full max-w-xl mx-auto mt-6 flex gap-3"
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
                disabled={!customVibe.trim() || moodLoading}
                className="h-12 px-6 bg-primary text-on-primary rounded-full font-label font-bold text-sm tracking-wide hover:shadow-[0_0_20px_rgba(255,193,7,0.3)] transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                Discover
              </button>
            </form>
          </div>
        </section>

        {/* Mood Results */}
        {(selectedMood || moodLoading) && (
          <MoodCarousel
            mood={selectedMood ?? ""}
            movies={moodMovies}
            loading={moodLoading}
            isPersonalized={moodPersonalized}
            isBookmarked={isInWatchlist}
            onToggleBookmark={toggle}
          />
        )}

        {/* Recommendations Section */}
        <section className="max-w-7xl mx-auto px-6 pb-32">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
            {/* Control Panel */}
            <div className="lg:col-span-5 glass-panel p-10 rounded-2xl border border-outline-variant/10 space-y-10">
              <div className="space-y-2">
                <h2 className="font-headline text-3xl font-bold text-on-surface">
                  Get Recommendations
                </h2>
                <p className="font-body text-on-surface-variant">
                  Personalized curation powered by neural engines.
                </p>
              </div>
              <form onSubmit={handleRecs} className="space-y-8">
                <div className="space-y-3">
                  <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                    Member ID
                  </label>
                  <div className="relative glowing-border rounded-lg">
                    <div className="w-full bg-surface-container-lowest rounded-lg p-4 text-on-surface font-mono">
                      USR-{userId}
                    </div>
                  </div>
                </div>
                <div className="space-y-3">
                  <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                    Discovery Engine
                  </label>
                  <div className="relative">
                    <select
                      value={strategy}
                      onChange={(e) => setStrategy(e.target.value)}
                      className="w-full bg-surface-container-lowest border-none rounded-lg p-4 text-on-surface appearance-none focus:ring-2 focus:ring-surface-tint font-body"
                    >
                      <option value="hybrid">Hybrid (Balanced)</option>
                      <option value="content">Content Based (Genre Focus)</option>
                      <option value="collab">Collaborative (Peer Trends)</option>
                    </select>
                    <div className="absolute inset-y-0 right-4 flex items-center pointer-events-none">
                      <span className="material-symbols-outlined text-outline">
                        expand_more
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  type="submit"
                  className="w-full py-5 bg-gradient-to-r from-primary to-primary-fixed-dim text-on-primary-container font-headline font-extrabold text-lg rounded-lg shadow-[0_0_30px_rgba(255,193,7,0.2)] hover:shadow-[0_0_45px_rgba(255,193,7,0.4)] transition-all duration-300 active:scale-[0.98]"
                >
                  GET RECOMMENDATIONS
                </button>
              </form>
            </div>
            {/* Movie Carousels */}
            <div className="lg:col-span-7 space-y-10">
              {popular.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-headline font-bold text-xl text-on-surface">Popular Now</h3>
                    <Link to="/discover?sort_by=popularity" className="text-primary text-sm font-medium hover:underline">
                      See all &rarr;
                    </Link>
                  </div>
                  <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
                    {popular.map((m) => (
                      <div key={m.id} className="flex-shrink-0 w-44">
                        <MovieCard movie={m} isBookmarked={isInWatchlist(m.id)} onToggleBookmark={toggle} />
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {topRated.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="font-headline font-bold text-xl text-on-surface">Top Rated</h3>
                    <Link to="/discover?sort_by=vote_average" className="text-primary text-sm font-medium hover:underline">
                      See all &rarr;
                    </Link>
                  </div>
                  <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
                    {topRated.map((m) => (
                      <div key={m.id} className="flex-shrink-0 w-44">
                        <MovieCard movie={m} isBookmarked={isInWatchlist(m.id)} onToggleBookmark={toggle} />
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </section>
      </main>
      <BottomNav />
    </>
  );
}
