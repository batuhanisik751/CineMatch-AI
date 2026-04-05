import BottomNav from "../../components/BottomNav";
import Sidebar from "../../components/Sidebar";
import TabLayout from "../../components/TabLayout";
import TopNav from "../../components/TopNav";

const TABS = [
  { label: "Overview",        icon: "person",    path: "overview" },
  { label: "Taste Evolution", icon: "timeline",  path: "taste-evolution" },
  { label: "Platform Stats",  icon: "bar_chart", path: "platform-stats" },
  { label: "Audit Log",       icon: "security",    path: "audit-log" },
  { label: "DB Security",     icon: "shield_lock", path: "db-security" },
  { label: "Pickle Safety",   icon: "verified_user", path: "pickle-safety" },
  { label: "Container Security", icon: "deployed_code", path: "container-security" },
  { label: "Dep Scan", icon: "bug_report", path: "dep-scan" },
];

export default function ProfileLayout() {
  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <TabLayout tabs={TABS} baseRoute="/profile" />
        </div>
      </main>
      <BottomNav />
    </>
  );
}
