import { Link, useLocation } from "react-router-dom";

const items = [
  { to: "/", icon: "home", label: "Home" },
  { to: "/discover", icon: "explore", label: "Discover" },
  { to: "/search", icon: "search", label: "Search" },
  { to: "/explore", icon: "theater_comedy", label: "Explore" },
  { to: "/collections", icon: "collections_bookmark", label: "Collections" },
  { to: "/director-gaps", icon: "person_search", label: "Director Gaps" },
  { to: "/curated", icon: "auto_awesome_mosaic", label: "Curated" },
  { to: "/for-you", icon: "auto_awesome", label: "For You" },
  { to: "/watchlist", icon: "bookmark", label: "Watchlist" },
  { to: "/lists", icon: "playlist_add", label: "My Lists" },
  { to: "/taste-evolution", icon: "timeline", label: "Taste Evolution" },
  { to: "/challenges", icon: "flag", label: "Challenges" },
  { to: "/achievements", icon: "emoji_events", label: "Achievements" },
  { to: "/bingo", icon: "grid_view", label: "Movie Bingo" },
  { to: "/platform-stats", icon: "bar_chart", label: "Platform Stats" },
  { to: "/profile", icon: "person", label: "Profile" },
];

export default function Sidebar() {
  const { pathname } = useLocation();

  return (
    <aside className="hidden lg:flex flex-col p-6 gap-2 h-full w-64 fixed left-0 top-20 bg-[#0e0e0f] border-r border-white/5">
      <div className="mb-8 px-4">
        <span className="text-[#FFC107] font-black italic font-headline">
          Private Screening
        </span>
        <p className="text-xs text-on-surface-variant uppercase tracking-widest font-medium">
          Premium Member
        </p>
      </div>
      <nav className="flex flex-col gap-1 overflow-y-auto flex-1 min-h-0">
        {items.map((item) => {
          const active =
            (item.to === "/" && pathname === "/") ||
            (item.to !== "/" && pathname.startsWith(item.to));
          return (
            <Link
              key={item.to}
              to={item.to}
              className={
                active
                  ? "flex items-center gap-3 bg-[#FFC107] text-[#131314] rounded-lg px-4 py-3 shadow-[0_0_15px_rgba(255,193,7,0.3)] font-headline text-sm font-medium"
                  : "flex items-center gap-3 text-[#d4c5ab] px-4 py-3 hover:bg-[#201f20] rounded-lg transition-all hover:translate-x-1 duration-200 font-headline text-sm font-medium"
              }
            >
              <span
                className="material-symbols-outlined"
                style={
                  active
                    ? { fontVariationSettings: "'FILL' 1" }
                    : undefined
                }
              >
                {item.icon}
              </span>
              {item.label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
