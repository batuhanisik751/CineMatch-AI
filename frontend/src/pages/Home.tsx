import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { discoverMovies, getHiddenGems, semanticSearchMovies } from "../api/movies";
import { getOnboardingStatus } from "../api/onboarding";
import { getMoodRecommendations, getSurpriseMovies } from "../api/recommendations";
import type { FeedResponse, MovieSummary, RewatchItem } from "../api/types";
import { getUserFeed, getUserRewatch } from "../api/users";
import AddToListModal from "../components/AddToListModal";
import AutocompleteSearch from "../components/AutocompleteSearch";
import BottomNav from "../components/BottomNav";
import MoodCarousel from "../components/MoodCarousel";
import MoodPills from "../components/MoodPills";
import MovieCard from "../components/MovieCard";
import TopNav from "../components/TopNav";
import type { MoodPreset } from "../constants/moods";
import { useDismissed } from "../hooks/useDismissed";
import { useRated } from "../hooks/useRated";
import { useUserId } from "../hooks/useUserId";
import { useMatchPredictions } from "../hooks/useMatchPredictions";
import { useWatchlist } from "../hooks/useWatchlist";

export default function Home() {
  const navigate = useNavigate();
  const { userId } = useUserId();
  const [strategy, setStrategy] = useState("hybrid");
  const [popular, setPopular] = useState<MovieSummary[]>([]);
  const [topRated, setTopRated] = useState<MovieSummary[]>([]);
  const [gems, setGems] = useState<MovieSummary[]>([]);
  const { isInWatchlist, toggle, refreshForMovieIds } = useWatchlist();
  const { isDismissed, toggleDismiss, refreshDismissedForMovieIds } = useDismissed();
  const { getRating, refreshRatingsForMovieIds } = useRated();
  const { getMatchPercent, fetchMatchPercents } = useMatchPredictions();
  const [addToListMovieId, setAddToListMovieId] = useState<number | null>(null);

  const [selectedMood, setSelectedMood] = useState<string | null>(null);
  const [moodMovies, setMoodMovies] = useState<MovieSummary[]>([]);
  const [moodLoading, setMoodLoading] = useState(false);
  const [moodPersonalized, setMoodPersonalized] = useState(false);
  const [customVibe, setCustomVibe] = useState("");
  const moodAbort = useRef<AbortController | null>(null);
  const moodFallback = useRef(false);

  const [surpriseMovies, setSurpriseMovies] = useState<MovieSummary[]>([]);
  const [surpriseLoading, setSurpriseLoading] = useState(false);
  const [surpriseGenres, setSurpriseGenres] = useState<string[]>([]);

  const [feed, setFeed] = useState<FeedResponse | null>(null);
  const [feedLoading, setFeedLoading] = useState(false);

  const [rewatchItems, setRewatchItems] = useState<RewatchItem[]>([]);
  const [rewatchLoading, setRewatchLoading] = useState(false);

  const [onboardingNeeded, setOnboardingNeeded] = useState(false);
  const [onboardingRated, setOnboardingRated] = useState(0);
  const [onboardingThreshold, setOnboardingThreshold] = useState(10);
  const onboardingChecked = useRef(false);

  useEffect(() => {
    if (!userId || onboardingChecked.current) return;
    onboardingChecked.current = true;
    getOnboardingStatus(userId)
      .then((status) => {
        if (!status.completed) {
          setOnboardingNeeded(true);
          setOnboardingRated(status.rating_count);
          setOnboardingThreshold(status.threshold);
          // Auto-redirect on first visit only (no ratings at all)
          if (status.rating_count === 0) {
            navigate("/onboarding", { replace: true });
          }
        }
      })
      .catch(() => {});
  }, [userId, navigate]);

  useEffect(() => {
    discoverMovies({ sort_by: "popularity", limit: 8 })
      .then((data) => {
        setPopular(data.results);
        const ids = data.results.map((m) => m.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        refreshRatingsForMovieIds(ids);
        fetchMatchPercents(ids);
      })
      .catch(() => {});
    discoverMovies({ sort_by: "vote_average", limit: 8 })
      .then((data) => {
        setTopRated(data.results);
        const ids = data.results.map((m) => m.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        refreshRatingsForMovieIds(ids);
        fetchMatchPercents(ids);
      })
      .catch(() => {});
    getHiddenGems({ limit: 8 })
      .then((data) => {
        const movies = data.results.map((r) => r.movie);
        setGems(movies);
        const ids = movies.map((m) => m.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        refreshRatingsForMovieIds(ids);
        fetchMatchPercents(ids);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!userId) return;
    setFeedLoading(true);
    getUserFeed(userId)
      .then((data) => {
        setFeed(data);
        const allIds = data.sections.flatMap((s) => s.movies.map((m) => m.id));
        refreshForMovieIds(allIds);
        refreshDismissedForMovieIds(allIds);
        fetchMatchPercents(allIds);
      })
      .catch(() => setFeed(null))
      .finally(() => setFeedLoading(false));
  }, [userId]);

  useEffect(() => {
    if (!userId) return;
    setRewatchLoading(true);
    getUserRewatch(userId, 8)
      .then((data) => {
        setRewatchItems(data.suggestions);
        const ids = data.suggestions.map((s) => s.movie.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        refreshRatingsForMovieIds(ids);
        fetchMatchPercents(ids);
      })
      .catch(() => setRewatchItems([]))
      .finally(() => setRewatchLoading(false));
  }, [userId]);

  const feedSectionIcon: Record<string, string> = {
    because_you_rated: "thumb_up",
    trending_for_you: "trending_up",
    hidden_gems: "diamond",
    something_different: "explore",
    new_in_decade: "history",
    trending: "trending_up",
    top_rated: "star",
  };

  const handleRecs = (e: React.FormEvent) => {
    e.preventDefault();
    navigate(`/for-you/recommendations?user=${userId}&strategy=${strategy}`);
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
      const ids = movies.map((m) => m.id);
      refreshForMovieIds(ids);
      refreshDismissedForMovieIds(ids);
      fetchMatchPercents(ids);
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

  const handleSurprise = () => {
    if (!userId) return;
    setSurpriseLoading(true);
    getSurpriseMovies(userId, 8)
      .then((data) => {
        setSurpriseMovies(data.results);
        setSurpriseGenres(data.excluded_genres);
        const ids = data.results.map((m) => m.id);
        refreshForMovieIds(ids);
        refreshDismissedForMovieIds(ids);
        refreshRatingsForMovieIds(ids);
        fetchMatchPercents(ids);
      })
      .catch(() => setSurpriseMovies([]))
      .finally(() => setSurpriseLoading(false));
  };

  return (
    <>
      <TopNav />
      <main className="pt-20">
        {/* Onboarding Banner */}
        {onboardingNeeded && (
          <section className="max-w-7xl mx-auto px-6 pt-4">
            <div className="flex items-center justify-between gap-4 bg-primary-container rounded-xl px-6 py-4">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-2xl text-on-primary-container">
                  movie_filter
                </span>
                <div>
                  <p className="font-headline font-bold text-on-primary-container">
                    Complete your taste profile
                  </p>
                  <p className="text-sm text-on-primary-container/70">
                    Rate {onboardingThreshold - onboardingRated} more movie{onboardingThreshold - onboardingRated !== 1 ? "s" : ""} to unlock personalized recommendations
                  </p>
                </div>
              </div>
              <Link
                to="/onboarding"
                className="flex-shrink-0 px-5 py-2.5 bg-on-primary-container text-primary-container font-bold text-sm rounded-full hover:opacity-90 transition-opacity"
              >
                Continue
              </Link>
            </div>
          </section>
        )}

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
            <AutocompleteSearch
              placeholder="Search for titles, directors, or genres..."
              className="w-full max-w-2xl mx-auto mt-12"
              inputClassName="w-full h-16 pl-16 pr-6 bg-surface-container-lowest border-none rounded-xl text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint shadow-2xl transition-all duration-300 font-body text-lg"
              onNavigateToSearch={(q) => navigate(`/discover/browse?q=${encodeURIComponent(q)}`)}
            />
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
            <button
              onClick={handleSurprise}
              disabled={surpriseLoading}
              className="mt-6 h-14 px-8 bg-gradient-to-r from-tertiary to-tertiary-container text-on-tertiary-container rounded-full font-headline font-bold text-base tracking-wide hover:shadow-[0_0_25px_rgba(165,238,255,0.3)] transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-3 mx-auto"
            >
              <span className="material-symbols-outlined">casino</span>
              {surpriseLoading ? "Shuffling..." : "Surprise Me"}
            </button>
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
            isDismissed={isDismissed}
            onDismiss={toggleDismiss}
            getRating={getRating}
            getMatchPercent={getMatchPercent}
          />
        )}

        {/* Surprise Picks */}
        {surpriseMovies.length > 0 && (
          <section className="max-w-7xl mx-auto px-6 py-8">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="font-headline font-bold text-xl text-on-surface">
                  Surprise Picks
                </h3>
                {surpriseGenres.length > 0 && (
                  <p className="text-sm text-on-surface-variant mt-1">
                    Outside your usual {surpriseGenres.join(" & ")} favorites
                  </p>
                )}
              </div>
              <button
                onClick={handleSurprise}
                className="text-primary text-sm font-medium hover:underline flex items-center gap-1"
              >
                <span className="material-symbols-outlined text-sm">refresh</span>
                Shuffle again
              </button>
            </div>
            <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
              {surpriseMovies.map((m) => (
                <div key={m.id} className="flex-shrink-0 w-44">
                  <MovieCard
                    movie={m}
                    isBookmarked={isInWatchlist(m.id)}
                    onToggleBookmark={toggle}
                    onAddToList={(id) => setAddToListMovieId(id)}
                    isDismissed={isDismissed(m.id)}
                    onDismiss={toggleDismiss}
                    userRating={getRating(m.id)}
                    matchPercent={getMatchPercent(m.id)}
                  />
                </div>
              ))}
            </div>
          </section>
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
            {/* Movie Carousels — personalized feed or static fallback */}
            <div className="lg:col-span-7 space-y-10">
              {feed && feed.sections.length > 0 ? (
                <>
                  {feed.is_personalized && (
                    <div className="flex items-center gap-2 text-primary text-sm font-medium">
                      <span className="material-symbols-outlined text-base">auto_awesome</span>
                      Personalized for you
                    </div>
                  )}
                  {feed.sections.map((section) => (
                    <div key={section.key}>
                      <div className="flex items-center gap-2 mb-4">
                        <span className="material-symbols-outlined text-primary text-xl">
                          {feedSectionIcon[section.key] || "movie"}
                        </span>
                        <h3 className="font-headline font-bold text-xl text-on-surface">
                          {section.title}
                        </h3>
                      </div>
                      <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
                        {section.movies.map((m) => (
                          <div key={m.id} className="flex-shrink-0 w-44">
                            <MovieCard
                              movie={m}
                              isBookmarked={isInWatchlist(m.id)}
                              onToggleBookmark={toggle}
                              onAddToList={(id) => setAddToListMovieId(id)}
                              isDismissed={isDismissed(m.id)}
                              onDismiss={toggleDismiss}
                              userRating={getRating(m.id)}
                              matchPercent={getMatchPercent(m.id)}
                            />
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </>
              ) : feedLoading ? (
                <div className="space-y-10">
                  {[1, 2, 3].map((i) => (
                    <div key={i}>
                      <div className="h-6 w-48 bg-surface-container-low rounded mb-4 animate-pulse" />
                      <div className="flex gap-4 overflow-x-auto pb-4">
                        {[1, 2, 3, 4, 5, 6].map((j) => (
                          <div
                            key={j}
                            className="flex-shrink-0 w-44 aspect-[2/3] bg-surface-container-low rounded-xl animate-pulse"
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <>
                  {popular.length > 0 && (
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-headline font-bold text-xl text-on-surface">Popular Now</h3>
                        <Link to="/discover/browse?sort_by=popularity" className="text-primary text-sm font-medium hover:underline">
                          See all &rarr;
                        </Link>
                      </div>
                      <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
                        {popular.map((m) => (
                          <div key={m.id} className="flex-shrink-0 w-44">
                            <MovieCard movie={m} isBookmarked={isInWatchlist(m.id)} onToggleBookmark={toggle} onAddToList={(id) => setAddToListMovieId(id)} isDismissed={isDismissed(m.id)} onDismiss={toggleDismiss} userRating={getRating(m.id)} matchPercent={getMatchPercent(m.id)} />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {topRated.length > 0 && (
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-headline font-bold text-xl text-on-surface">Top Rated</h3>
                        <Link to="/discover/browse?sort_by=vote_average" className="text-primary text-sm font-medium hover:underline">
                          See all &rarr;
                        </Link>
                      </div>
                      <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
                        {topRated.map((m) => (
                          <div key={m.id} className="flex-shrink-0 w-44">
                            <MovieCard movie={m} isBookmarked={isInWatchlist(m.id)} onToggleBookmark={toggle} onAddToList={(id) => setAddToListMovieId(id)} isDismissed={isDismissed(m.id)} onDismiss={toggleDismiss} userRating={getRating(m.id)} matchPercent={getMatchPercent(m.id)} />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  {gems.length > 0 && (
                    <div>
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-headline font-bold text-xl text-on-surface">Hidden Gems</h3>
                        <Link to="/discover/hidden-gems" className="text-primary text-sm font-medium hover:underline">
                          See all &rarr;
                        </Link>
                      </div>
                      <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
                        {gems.map((m) => (
                          <div key={m.id} className="flex-shrink-0 w-44">
                            <MovieCard movie={m} isBookmarked={isInWatchlist(m.id)} onToggleBookmark={toggle} onAddToList={(id) => setAddToListMovieId(id)} isDismissed={isDismissed(m.id)} onDismiss={toggleDismiss} userRating={getRating(m.id)} matchPercent={getMatchPercent(m.id)} />
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </section>

        {/* Revisit Your Favorites */}
        <section className="max-w-7xl mx-auto px-6 pb-32">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-2xl text-primary">
                history
              </span>
              <div>
                <h2 className="font-headline font-bold text-2xl text-on-surface">
                  Revisit Your Favorites
                </h2>
                <p className="text-sm text-on-surface-variant mt-0.5">
                  Movies you loved long ago worth watching again
                </p>
              </div>
            </div>
            {rewatchItems.length > 0 && (
              <Link
                to="/for-you/rewatch"
                className="text-primary text-sm font-medium hover:underline flex items-center gap-1"
              >
                See all
                <span className="material-symbols-outlined text-sm">
                  arrow_forward
                </span>
              </Link>
            )}
          </div>

          {rewatchLoading && (
            <div className="flex gap-4 overflow-x-auto pb-4">
              {[1, 2, 3, 4, 5, 6].map((j) => (
                <div
                  key={j}
                  className="flex-shrink-0 w-44 aspect-[2/3] bg-surface-container-low rounded-xl animate-pulse"
                />
              ))}
            </div>
          )}

          {!rewatchLoading && rewatchItems.length === 0 && (
            <div className="glass-panel rounded-2xl border border-outline-variant/10 p-10 text-center">
              <span className="material-symbols-outlined text-5xl text-outline mb-3 block">
                history
              </span>
              <p className="text-on-surface-variant text-base mb-2">
                No old favorites to revisit yet
              </p>
              <p className="text-on-surface-variant/60 text-sm">
                Rate some movies and check back later — we'll remind you of the ones you loved!
              </p>
            </div>
          )}

          {!rewatchLoading && rewatchItems.length > 0 && (
            <div className="flex gap-4 overflow-x-auto pb-4 scrollbar-hide">
              {rewatchItems.map((item) => (
                <div key={item.movie.id} className="flex-shrink-0 w-44">
                  <MovieCard
                    movie={item.movie}
                    isBookmarked={isInWatchlist(item.movie.id)}
                    onToggleBookmark={toggle}
                    onAddToList={(id) => setAddToListMovieId(id)}
                    isDismissed={isDismissed(item.movie.id)}
                    onDismiss={toggleDismiss}
                    userRating={getRating(item.movie.id)}
                    matchPercent={getMatchPercent(item.movie.id)}
                  />
                  <p className="text-[11px] text-on-surface-variant/60 mt-1.5 px-1 flex items-center gap-1">
                    <span className="material-symbols-outlined text-[12px]">
                      schedule
                    </span>
                    Rated {item.user_rating}/10,{" "}
                    {Math.floor(item.days_since_rated / 365) > 0
                      ? `${Math.floor(item.days_since_rated / 365)}y ago`
                      : "recently"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
      <AddToListModal movieId={addToListMovieId} onClose={() => setAddToListMovieId(null)} />
      <BottomNav />
    </>
  );
}
