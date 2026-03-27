import { Link, useLocation } from "react-router-dom";

export default function TopNav() {
  const { pathname } = useLocation();

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

  return (
    <nav className="fixed top-0 w-full z-50 bg-[#131314]/80 backdrop-blur-xl border-b border-white/5 shadow-[0_20px_40px_rgba(0,0,0,0.6)] flex justify-between items-center px-8 h-20 font-headline tracking-tight text-on-surface">
      <Link
        to="/"
        className="text-2xl font-bold tracking-tighter text-[#FFC107] uppercase"
      >
        CINEMA PRIVATE
      </Link>
      <div className="hidden md:flex items-center gap-8">
        {navLink("/", "Home")}
        {navLink("/discover", "Discover")}
        {navLink("/recommendations", "Recommendations")}
        {navLink("/profile", "Profile")}
      </div>
      <div className="flex items-center gap-6">
        <div className="flex items-center gap-4">
          <button className="material-symbols-outlined text-[#d4c5ab] hover:text-[#FFC107] transition-all duration-300">
            notifications
          </button>
          <button className="material-symbols-outlined text-[#d4c5ab] hover:text-[#FFC107] transition-all duration-300">
            settings
          </button>
        </div>
      </div>
    </nav>
  );
}
