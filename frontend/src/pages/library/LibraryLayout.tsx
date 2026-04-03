import BottomNav from "../../components/BottomNav";
import Sidebar from "../../components/Sidebar";
import TabLayout from "../../components/TabLayout";
import TopNav from "../../components/TopNav";

const TABS = [
  { label: "Watchlist",   icon: "bookmark",             path: "watchlist" },
  { label: "My Lists",    icon: "playlist_add",         path: "lists" },
  { label: "Collections", icon: "collections_bookmark", path: "collections" },
  { label: "Gaps",        icon: "person_search",        path: "gaps" },
  { label: "Curated",     icon: "auto_awesome_mosaic",  path: "curated" },
];

export default function LibraryLayout() {
  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <TabLayout tabs={TABS} baseRoute="/library" />
        </div>
      </main>
      <BottomNav />
    </>
  );
}
