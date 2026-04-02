import { useRef } from "react";
import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import Achievements from "./pages/Achievements";
import Bingo from "./pages/Bingo";
import { ForYouLayout, RecommendationsTab, BlindSpotsTab, RewatchTab } from "./pages/for-you";
import { ExploreLayout, DirectorsTab, ActorsTab, CastComboTab, KeywordsTab } from "./pages/explore";
import Challenges from "./pages/Challenges";
import { SearchLayout, TitleTab, MoodTab, AdvancedTab } from "./pages/search";
import Collections from "./pages/Collections";
import Compare from "./pages/Compare";
import DirectorGaps from "./pages/DirectorGaps";
import Curated from "./pages/Curated";
import Diary from "./pages/Diary";
import { DiscoverLayout, BrowseTab, TrendingTab, TopChartsTab, HiddenGemsTab, SeasonalTab, ControversialTab, DecadesTab } from "./pages/discover";
import FromSeedRecommendations from "./pages/FromSeedRecommendations";
import Home from "./pages/Home";
import ListDetail from "./pages/ListDetail";
import Lists from "./pages/Lists";
import PopularLists from "./pages/PopularLists";
import MovieDetail from "./pages/MovieDetail";
import Onboarding from "./pages/Onboarding";
import PlatformStats from "./pages/PlatformStats";
import Profile from "./pages/Profile";
import TasteEvolution from "./pages/TasteEvolution";
import Watchlist from "./pages/Watchlist";
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
      <Route path="/collections" element={<Collections key={navCountRef.current} />} />
      <Route path="/director-gaps" element={<DirectorGaps key={navCountRef.current} />} />
      <Route path="/curated" element={<Curated key={navCountRef.current} />} />
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
      <Route path="/watchlist/recommendations" element={<WatchlistRecommendations />} />
      <Route path="/watchlist" element={<Watchlist />} />
      <Route path="/lists" element={<Lists />} />
      <Route path="/lists/popular" element={<PopularLists />} />
      <Route path="/lists/:id" element={<ListDetail key={navCountRef.current} />} />
      <Route path="/diary" element={<Diary />} />
      <Route path="/achievements" element={<Achievements />} />
      <Route path="/bingo" element={<Bingo />} />
      <Route path="/challenges" element={<Challenges />} />
      <Route path="/taste-evolution" element={<TasteEvolution />} />
      <Route path="/platform-stats" element={<PlatformStats />} />
      <Route path="/profile" element={<Profile />} />
    </Routes>
  );
}
