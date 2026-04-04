import { useRef } from "react";
import { Navigate, Route, Routes, useLocation, useParams } from "react-router-dom";
import { ActivityLayout, AchievementsTab, ChallengesTab, BingoTab, DiaryTab } from "./pages/activity";
import { ForYouLayout, RecommendationsTab, BlindSpotsTab, RewatchTab } from "./pages/for-you";
import { ExploreLayout, DirectorsTab, ActorsTab, KeywordsTab } from "./pages/explore";
import { SearchLayout } from "./pages/search";
import Compare from "./pages/Compare";
import { DiscoverLayout, BrowseTab, TrendingTab, TopChartsTab, HiddenGemsTab, SeasonalTab, ControversialTab, DecadesTab } from "./pages/discover";
import FromSeedRecommendations from "./pages/FromSeedRecommendations";
import Home from "./pages/Home";
import ListDetail from "./pages/ListDetail";
import PopularLists from "./pages/PopularLists";
import { LibraryLayout, WatchlistTab, ListsTab, CollectionsTab, CuratedTab } from "./pages/library";
import MovieDetail from "./pages/MovieDetail";
import Onboarding from "./pages/Onboarding";
import { ProfileLayout, OverviewTab, TasteEvolutionTab, PlatformStatsTab, AuditLogTab } from "./pages/profile";
import WatchlistRecommendations from "./pages/WatchlistRecommendations";
import LoginPage from "./pages/auth/LoginPage";
import RegisterPage from "./pages/auth/RegisterPage";
import ProtectedRoute from "./components/ProtectedRoute";

function RedirectToBrowse() {
  const location = useLocation();
  return <Navigate to={"browse" + location.search} replace />;
}

function RedirectToSearch() {
  const location = useLocation();
  return <Navigate to={"/search" + location.search} replace />;
}

function RedirectToDirectors() {
  const location = useLocation();
  return <Navigate to={"directors" + location.search} replace />;
}

function RedirectToRecommendations() {
  const location = useLocation();
  return <Navigate to={"recommendations" + location.search} replace />;
}

function LegacyRedirect({ to }: { to: string }) {
  const location = useLocation();
  return <Navigate to={to + location.search} replace />;
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
      {/* Public auth routes */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      {/* Public discovery routes */}
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
      <Route path="/search" element={<SearchLayout />} />
      <Route path="/search/title" element={<RedirectToSearch />} />
      <Route path="/search/mood" element={<RedirectToSearch />} />
      <Route path="/search/advanced" element={<RedirectToSearch />} />
      <Route path="/explore" element={<ExploreLayout />}>
        <Route index element={<RedirectToDirectors />} />
        <Route path="directors" element={<DirectorsTab />} />
        <Route path="actors" element={<ActorsTab />} />
        <Route path="cast-combo" element={<Navigate to="/explore/actors" replace />} />
        <Route path="keywords" element={<KeywordsTab />} />
      </Route>
      <Route path="/compare" element={<Compare />} />
      <Route path="/movies/:id" element={<MovieDetail />} />
      <Route path="/recommendations/from-seed/:movieId" element={<FromSeedRecommendations />} />

      {/* Protected routes */}
      <Route element={<ProtectedRoute />}>
        <Route path="/onboarding" element={<Onboarding />} />
        <Route path="/" element={<Home />} />
        <Route path="/library" element={<LibraryLayout />}>
          <Route index element={<RedirectToWatchlist />} />
          <Route path="watchlist" element={<WatchlistTab />} />
          <Route path="lists" element={<ListsTab />} />
          <Route path="collections" element={<CollectionsTab key={navCountRef.current} />} />
          <Route path="gaps" element={<Navigate to="/library/collections" replace />} />
          <Route path="curated" element={<CuratedTab key={navCountRef.current} />} />
        </Route>
        <Route path="/library/watchlist/recommendations" element={<WatchlistRecommendations />} />
        <Route path="/library/lists/popular" element={<PopularLists />} />
        <Route path="/library/lists/:id" element={<ListDetail key={navCountRef.current} />} />
        <Route path="/for-you" element={<ForYouLayout />}>
          <Route index element={<RedirectToRecommendations />} />
          <Route path="recommendations" element={<RecommendationsTab />} />
          <Route path="blind-spots" element={<BlindSpotsTab />} />
          <Route path="rewatch" element={<RewatchTab />} />
        </Route>
        <Route path="/activity" element={<ActivityLayout />}>
          <Route index element={<RedirectToAchievements />} />
          <Route path="achievements" element={<AchievementsTab />} />
          <Route path="challenges" element={<ChallengesTab />} />
          <Route path="bingo" element={<BingoTab />} />
          <Route path="diary" element={<DiaryTab />} />
        </Route>
        <Route path="/profile" element={<ProfileLayout />}>
          <Route index element={<RedirectToOverview />} />
          <Route path="overview" element={<OverviewTab />} />
          <Route path="taste-evolution" element={<TasteEvolutionTab />} />
          <Route path="platform-stats" element={<PlatformStatsTab />} />
          <Route path="audit-log" element={<AuditLogTab />} />
        </Route>
      </Route>

      {/* Legacy discover redirects */}
      <Route path="/trending" element={<LegacyRedirect to="/discover/trending" />} />
      <Route path="/top-charts" element={<LegacyRedirect to="/discover/top-charts" />} />
      <Route path="/hidden-gems" element={<LegacyRedirect to="/discover/hidden-gems" />} />
      <Route path="/seasonal" element={<LegacyRedirect to="/discover/seasonal" />} />
      <Route path="/controversial" element={<LegacyRedirect to="/discover/controversial" />} />
      <Route path="/decades" element={<LegacyRedirect to="/discover/decades" />} />
      {/* Legacy search redirects */}
      <Route path="/moods" element={<LegacyRedirect to="/search" />} />
      <Route path="/advanced-search" element={<LegacyRedirect to="/search" />} />
      {/* Legacy explore redirects */}
      <Route path="/directors" element={<LegacyRedirect to="/explore/directors" />} />
      <Route path="/actors" element={<LegacyRedirect to="/explore/actors" />} />
      <Route path="/cast-combo" element={<LegacyRedirect to="/explore/actors" />} />
      <Route path="/keywords" element={<LegacyRedirect to="/explore/keywords" />} />
      {/* Legacy for-you redirects */}
      <Route path="/recommendations" element={<LegacyRedirect to="/for-you/recommendations" />} />
      <Route path="/blind-spots" element={<LegacyRedirect to="/for-you/blind-spots" />} />
      <Route path="/rewatch" element={<LegacyRedirect to="/for-you/rewatch" />} />
      {/* Legacy library redirects */}
      <Route path="/watchlist/recommendations" element={<LegacyRedirect to="/library/watchlist/recommendations" />} />
      <Route path="/watchlist" element={<LegacyRedirect to="/library/watchlist" />} />
      <Route path="/lists/popular" element={<LegacyRedirect to="/library/lists/popular" />} />
      <Route path="/lists/:id" element={<LegacyListDetailRedirect />} />
      <Route path="/lists" element={<LegacyRedirect to="/library/lists" />} />
      <Route path="/collections" element={<LegacyRedirect to="/library/collections" />} />
      <Route path="/director-gaps" element={<LegacyRedirect to="/library/collections" />} />
      <Route path="/curated" element={<LegacyRedirect to="/library/curated" />} />
      {/* Legacy activity redirects */}
      <Route path="/achievements" element={<LegacyRedirect to="/activity/achievements" />} />
      <Route path="/challenges" element={<LegacyRedirect to="/activity/challenges" />} />
      <Route path="/bingo" element={<LegacyRedirect to="/activity/bingo" />} />
      <Route path="/diary" element={<LegacyRedirect to="/activity/diary" />} />
      {/* Legacy profile redirects */}
      <Route path="/taste-evolution" element={<LegacyRedirect to="/profile/taste-evolution" />} />
      <Route path="/platform-stats" element={<LegacyRedirect to="/profile/platform-stats" />} />
      {/* Catch-all 404 */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
