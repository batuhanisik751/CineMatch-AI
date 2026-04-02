import BottomNav from "../../components/BottomNav";
import Sidebar from "../../components/Sidebar";
import TabLayout from "../../components/TabLayout";
import TopNav from "../../components/TopNav";

const TABS = [
  { label: "Directors",  icon: "movie_filter",   path: "directors" },
  { label: "Actors",     icon: "theater_comedy",  path: "actors" },
  { label: "Cast Combo", icon: "group",           path: "cast-combo" },
  { label: "Keywords",   icon: "sell",            path: "keywords" },
];

export default function ExploreLayout() {
  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <TabLayout tabs={TABS} baseRoute="/explore" />
        </div>
      </main>
      <BottomNav />
    </>
  );
}
