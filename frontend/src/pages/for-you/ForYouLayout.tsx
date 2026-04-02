import BottomNav from "../../components/BottomNav";
import Sidebar from "../../components/Sidebar";
import TabLayout from "../../components/TabLayout";
import TopNav from "../../components/TopNav";

const TABS = [
  { label: "Recommendations", icon: "auto_awesome",   path: "recommendations" },
  { label: "Blind Spots",     icon: "visibility_off",  path: "blind-spots" },
  { label: "Rewatch",         icon: "history",          path: "rewatch" },
];

export default function ForYouLayout() {
  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <TabLayout tabs={TABS} baseRoute="/for-you" />
        </div>
      </main>
      <BottomNav />
    </>
  );
}
