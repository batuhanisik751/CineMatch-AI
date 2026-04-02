import BottomNav from "../../components/BottomNav";
import Sidebar from "../../components/Sidebar";
import TabLayout from "../../components/TabLayout";
import TopNav from "../../components/TopNav";

const TABS = [
  { label: "Title",       icon: "search", path: "title" },
  { label: "Vibe & Mood", icon: "mood",   path: "mood" },
  { label: "Advanced",    icon: "tune",   path: "advanced" },
];

export default function SearchLayout() {
  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <TabLayout tabs={TABS} baseRoute="/search" />
        </div>
      </main>
      <BottomNav />
    </>
  );
}
