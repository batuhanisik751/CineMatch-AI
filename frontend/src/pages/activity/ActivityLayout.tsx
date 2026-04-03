import BottomNav from "../../components/BottomNav";
import Sidebar from "../../components/Sidebar";
import TabLayout from "../../components/TabLayout";
import TopNav from "../../components/TopNav";

const TABS = [
  { label: "Achievements", icon: "emoji_events",  path: "achievements" },
  { label: "Challenges",   icon: "flag",           path: "challenges" },
  { label: "Bingo",        icon: "grid_view",      path: "bingo" },
  { label: "Diary",        icon: "calendar_month", path: "diary" },
];

export default function ActivityLayout() {
  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <TabLayout tabs={TABS} baseRoute="/activity" />
        </div>
      </main>
      <BottomNav />
    </>
  );
}
