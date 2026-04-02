import BottomNav from "../../components/BottomNav";
import Sidebar from "../../components/Sidebar";
import TabLayout from "../../components/TabLayout";
import TopNav from "../../components/TopNav";

const TABS = [
  { label: "Browse",        icon: "explore",        path: "browse" },
  { label: "Trending",      icon: "trending_up",    path: "trending" },
  { label: "Top Charts",    icon: "leaderboard",    path: "top-charts" },
  { label: "Hidden Gems",   icon: "diamond",        path: "hidden-gems" },
  { label: "Seasonal",      icon: "calendar_month", path: "seasonal" },
  { label: "Controversial", icon: "whatshot",        path: "controversial" },
  { label: "Decades",       icon: "history",        path: "decades" },
];

export default function DiscoverLayout() {
  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <TabLayout tabs={TABS} baseRoute="/discover" />
        </div>
      </main>
      <BottomNav />
    </>
  );
}
