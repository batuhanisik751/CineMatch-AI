import { useRef } from "react";
import { Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";
import { ActivityLayout, AchievementsTab, ChallengesTab, BingoTab, DiaryTab } from "./pages/activity";
import { ForYouLayout, RecommendationsTab, BlindSpotsTab, RewatchTab } from "./pages/for-you";
import { ExploreLayout, DirectorsTab, ActorsTab, CastComboTab, KeywordsTab } from "./pages/explore";
import { SearchLayout, TitleTab, MoodTab, AdvancedTab } from "./pages/search";
import Compare from "./pages/Compare";
import { DiscoverLayout, BrowseTab, TrendingTab, TopChartsTab, HiddenGemsTab, SeasonalTab, ControversialTab, DecadesTab } from "./pages/discover";
import FromSeedRecommendations from "./pages/FromSeedRecommendations";
import Home from "./pages/Home";
import ListDetail from "./pages/ListDetail";
import PopularLists from "./pages/PopularLists";
import { LibraryLayout, WatchlistTab, ListsTab, CollectionsTab, GapsTab, CuratedTab } from "./pages/library";
import MovieDetail from "./pages/MovieDetail";
import Onboarding from "./pages/Onboarding";
import { ProfileLayout, OverviewTab, TasteEvolutionTab, PlatformStatsTab } from "./pages/profile";
import WatchlistRecommendations from "./pages/WatchlistRecommendations";

function RedirectToBrowse() {
  const location = useLocation();
  return <Navigate to={"browse" + location.search} replace />;
}

function RedirectToTitle() {
  const location = useLocation();
  return <Navigate to={"title" + location.search} replace />;
}

function RedirectToDirectors() {
  const location = useLocation();
  return <Navigate to={"directors" + location.search} replace />;
}

function RedirectToRecommendations() {
  const location = useLocation();
  return <Navigate to={"recommendations" + location.search} replace />;
}

function LegacyRecsRedirect() {
  const location = useLocation();
  return <Navigate to={"/for-you/recommendations" + location.search} replace />;
}

function RedirectToWatchlist() {
  const location = useLocation();
  return <Navigate to={"watchlist" + location.search} replace />;
}

function RedirectToAchievements() {
  const location = useLocation();
  return <Navigate to={"achievements" + location.search} replace />;
}

function RedirectToOverview() {
  const location = useLocation();
  return <Navigate to={"overview" + location.search} replace />;
}

function LegacyListDetailRedirect() {
  const { id } = useParams();
  return <Navigate to={`/library/lists/${id}`} replace />;
}

export default function App() {
  const location = useLocation();
  const navCountRef = useRef(0);
  const prevLocationRef = useRef(location);

  // Increment counter on every navigation (including browser back/forward)
  // so keyed routes always get a fresh mount
  if (location !== prevLocationRef.current) {
    navCountRef.current++;
    prevLocationRef.current = location;
  }

  return (
    <Routes>
      <Route path="/onboarding" element={<Onboarding />} />
      <Route path="/" element={<Home />} />
      <Route path="/discover" element={<DiscoverLayout />}>
        <Route index element={<RedirectToBrowse />} />
        <Route path="browse" element={<BrowseTab />} />
        <Route path="trending" element={<TrendingTab />} />
        <Route path="top-charts" element={<TopChartsTab />} />
        <Route path="hidden-gems" element={<HiddenGemsTab />} />
        <Route path="seasonal" element={<SeasonalTab />} />
        <Route path="controversial" element={<ControversialTab />} />
        <Route path="decades" element={<DecadesTab key={navCountRef.current} />} />
      </Route>
      <Route path="/search" element={<SearchLayout />}>
        <Route index element={<RedirectToTitle />} />
        <Route path="title" element={<TitleTab />} />
        <Route path="mood" element={<MoodTab />} />
        <Route path="advanced" element={<AdvancedTab />} />
      </Route>
      <Route path="/explore" element={<ExploreLayout />}>
        <Route index element={<RedirectToDirectors />} />
        <Route path="directors" element={<DirectorsTab />} />
        <Route path="actors" element={<ActorsTab />} />
        <Route path="cast-combo" element={<CastComboTab />} />
        <Route path="keywords" element={<KeywordsTab />} />
      </Route>
      <Route path="/library" element={<LibraryLayout />}>
        <Route index element={<RedirectToWatchlist />} />
        <Route path="watchlist" element={<WatchlistTab />} />
        <Route path="lists" element={<ListsTab />} />
        <Route path="collections" element={<CollectionsTab key={navCountRef.current} />} />
        <Route path="gaps" element={<GapsTab key={navCountRef.current} />} />
        <Route path="curated" element={<CuratedTab key={navCountRef.current} />} />
      </Route>
      <Route path="/library/watchlist/recommendations" element={<WatchlistRecommendations />} />
      <Route path="/library/lists/popular" element={<PopularLists />} />
      <Route path="/library/lists/:id" element={<ListDetail key={navCountRef.current} />} />
      <Route path="/compare" element={<Compare />} />
      <Route path="/movies/:id" element={<MovieDetail />} />
      <Route path="/for-you" element={<ForYouLayout />}>
        <Route index element={<RedirectToRecommendations />} />
        <Route path="recommendations" element={<RecommendationsTab />} />
        <Route path="blind-spots" element={<BlindSpotsTab />} />
        <Route path="rewatch" element={<RewatchTab />} />
      </Route>
      <Route path="/recommendations/from-seed/:movieId" element={<FromSeedRecommendations />} />
      <Route path="/recommendations" element={<LegacyRecsRedirect />} />
      <Route path="/blind-spots" element={<Navigate to="/for-you/blind-spots" replace />} />
      <Route path="/rewatch" element={<Navigate to="/for-you/rewatch" replace />} />
      {/* Legacy redirects for library pages */}
      <Route path="/watchlist/recommendations" element={<Navigate to="/library/watchlist/recommendations" replace />} />
      <Route path="/watchlist" element={<Navigate to="/library/watchlist" replace />} />
      <Route path="/lists/popular" element={<Navigate to="/library/lists/popular" replace />} />
      <Route path="/lists/:id" element={<LegacyListDetailRedirect />} />
      <Route path="/lists" element={<Navigate to="/library/lists" replace />} />
      <Route path="/collections" element={<Navigate to="/library/collections" replace />} />
      <Route path="/director-gaps" element={<Navigate to="/library/gaps" replace />} />
      <Route path="/curated" element={<Navigate to="/library/curated" replace />} />
      <Route path="/activity" element={<ActivityLayout />}>
        <Route index element={<RedirectToAchievements />} />
        <Route path="achievements" element={<AchievementsTab />} />
        <Route path="challenges" element={<ChallengesTab />} />
        <Route path="bingo" element={<BingoTab />} />
        <Route path="diary" element={<DiaryTab />} />
      </Route>
      {/* Legacy activity redirects */}
      <Route path="/achievements" element={<Navigate to="/activity/achievements" replace />} />
      <Route path="/challenges" element={<Navigate to="/activity/challenges" replace />} />
      <Route path="/bingo" element={<Navigate to="/activity/bingo" replace />} />
      <Route path="/diary" element={<Navigate to="/activity/diary" replace />} />
      <Route path="/profile" element={<ProfileLayout />}>
        <Route index element={<RedirectToOverview />} />
        <Route path="overview" element={<OverviewTab />} />
        <Route path="taste-evolution" element={<TasteEvolutionTab />} />
        <Route path="platform-stats" element={<PlatformStatsTab />} />
      </Route>
      {/* Legacy profile redirects */}
      <Route path="/taste-evolution" element={<Navigate to="/profile/taste-evolution" replace />} />
      <Route path="/platform-stats" element={<Navigate to="/profile/platform-stats" replace />} />
    </Routes>
  );
}
