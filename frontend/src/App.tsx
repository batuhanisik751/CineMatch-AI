import { Route, Routes } from "react-router-dom";
import Decades from "./pages/Decades";
import Discover from "./pages/Discover";
import HiddenGems from "./pages/HiddenGems";
import Home from "./pages/Home";
import MovieDetail from "./pages/MovieDetail";
import Profile from "./pages/Profile";
import Recommendations from "./pages/Recommendations";
import Search from "./pages/Search";
import TopCharts from "./pages/TopCharts";
import Trending from "./pages/Trending";
import Watchlist from "./pages/Watchlist";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/discover" element={<Discover />} />
      <Route path="/trending" element={<Trending />} />
      <Route path="/top-charts" element={<TopCharts />} />
      <Route path="/hidden-gems" element={<HiddenGems />} />
      <Route path="/decades" element={<Decades />} />
      <Route path="/search" element={<Search />} />
      <Route path="/movies/:id" element={<MovieDetail />} />
      <Route path="/recommendations" element={<Recommendations />} />
      <Route path="/watchlist" element={<Watchlist />} />
      <Route path="/profile" element={<Profile />} />
    </Routes>
  );
}
