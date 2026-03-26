import { Route, Routes } from "react-router-dom";
import Home from "./pages/Home";
import MovieDetail from "./pages/MovieDetail";
import Profile from "./pages/Profile";
import Recommendations from "./pages/Recommendations";
import Search from "./pages/Search";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/search" element={<Search />} />
      <Route path="/movies/:id" element={<MovieDetail />} />
      <Route path="/recommendations" element={<Recommendations />} />
      <Route path="/profile" element={<Profile />} />
    </Routes>
  );
}
