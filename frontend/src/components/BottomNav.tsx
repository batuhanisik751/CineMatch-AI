import { Link, useLocation } from "react-router-dom";

const items = [
  { to: "/", icon: "home", label: "Home" },
  { to: "/discover", icon: "explore", label: "Discover" },
  { to: "/search", icon: "search", label: "Search" },
  { to: "/for-you", icon: "auto_awesome", label: "For You" },
  { to: "/watchlist", icon: "bookmark", label: "Watchlist" },
  { to: "/lists", icon: "playlist_add", label: "Lists" },
  { to: "/profile", icon: "person", label: "Profile" },
];

export default function BottomNav() {
  const { pathname } = useLocation();

  return (
    <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-[#131314]/90 backdrop-blur-lg border-t border-white/5 h-20 flex items-center justify-around z-50">
      {items.map((item) => {
        const active =
          (item.to === "/" && pathname === "/") ||
          (item.to !== "/" && pathname.startsWith(item.to));
        return (
          <Link
            key={item.to}
            to={item.to}
            className={`flex flex-col items-center gap-1 ${active ? "text-[#FFC107]" : "text-[#d4c5ab]"}`}
          >
            <span
              className="material-symbols-outlined"
              style={active ? { fontVariationSettings: "'FILL' 1" } : undefined}
            >
              {item.icon}
            </span>
            <span className="text-[10px] font-bold uppercase tracking-widest">
              {item.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
