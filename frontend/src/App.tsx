import { useRef } from "react";
import { Route, Routes, useLocation } from "react-router-dom";
import Actors from "./pages/Actors";
import AdvancedSearch from "./pages/AdvancedSearch";
import Decades from "./pages/Decades";
import Directors from "./pages/Directors";
import Discover from "./pages/Discover";
import HiddenGems from "./pages/HiddenGems";
import Home from "./pages/Home";
import Keywords from "./pages/Keywords";
import MovieDetail from "./pages/MovieDetail";
import Profile from "./pages/Profile";
import Recommendations from "./pages/Recommendations";
import Search from "./pages/Search";
import TopCharts from "./pages/TopCharts";
import Trending from "./pages/Trending";
import Watchlist from "./pages/Watchlist";

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
      <Route path="/" element={<Home />} />
      <Route path="/discover" element={<Discover />} />
      <Route path="/trending" element={<Trending />} />
      <Route path="/top-charts" element={<TopCharts />} />
      <Route path="/hidden-gems" element={<HiddenGems />} />
      <Route path="/decades" element={<Decades key={navCountRef.current} />} />
      <Route path="/directors" element={<Directors key={navCountRef.current} />} />
      <Route path="/actors" element={<Actors key={navCountRef.current} />} />
      <Route path="/keywords" element={<Keywords key={navCountRef.current} />} />
      <Route path="/advanced-search" element={<AdvancedSearch />} />
      <Route path="/search" element={<Search />} />
      <Route path="/movies/:id" element={<MovieDetail />} />
      <Route path="/recommendations" element={<Recommendations />} />
      <Route path="/watchlist" element={<Watchlist />} />
      <Route path="/profile" element={<Profile />} />
    </Routes>
  );
}
