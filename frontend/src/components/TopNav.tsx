import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";

export default function TopNav() {
  const { pathname } = useLocation();
  const { isAuthenticated, username, logout } = useAuth();
  const navigate = useNavigate();

  const navLink = (to: string, label: string) => {
    const active =
      (to === "/" && pathname === "/") ||
      (to !== "/" && pathname.startsWith(to));
    return (
      <Link
        to={to}
        className={
          active
            ? "text-[#FFC107] font-bold border-b-2 border-[#FFC107] pb-1"
            : "text-[#d4c5ab] hover:text-[#FFC107] transition-colors"
        }
      >
        {label}
      </Link>
    );
  };

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <nav className="fixed top-0 w-full z-50 bg-[#131314]/80 backdrop-blur-xl border-b border-white/5 shadow-[0_20px_40px_rgba(0,0,0,0.6)] flex justify-between items-center px-8 h-20 font-headline tracking-tight text-on-surface">
      <Link
        to="/"
        className="text-2xl font-bold tracking-tighter text-[#FFC107] uppercase"
      >
        CINEMA PRIVATE
      </Link>
      <div className="hidden md:flex items-center gap-5">
        {navLink("/", "Home")}
        {navLink("/discover", "Discover")}
        {navLink("/search", "Search")}
        {navLink("/explore", "Explore")}
        {navLink("/for-you", "For You")}
        {navLink("/library", "Library")}
        {navLink("/activity", "Activity")}
        {navLink("/profile", "Profile")}
      </div>
      <div className="flex items-center gap-4">
        {isAuthenticated ? (
          <>
            <span className="text-[#d4c5ab] text-sm hidden sm:inline">{username}</span>
            <button
              onClick={handleLogout}
              className="text-[#FFC107] hover:text-[#ffca2c] transition-colors text-sm font-medium"
            >
              Logout
            </button>
          </>
        ) : (
          <Link
            to="/login"
            className="text-[#FFC107] hover:text-[#ffca2c] transition-colors text-sm font-medium"
          >
            Login
          </Link>
        )}
      </div>
    </nav>
  );
}
