import BottomNav from "../../components/BottomNav";
import Sidebar from "../../components/Sidebar";
import TopNav from "../../components/TopNav";
import SearchPage from "./SearchPage";

export default function SearchLayout() {
  return (
    <>
      <TopNav />
      <Sidebar />
      <main className="pt-32 pb-20 px-6 lg:ml-64 min-h-screen">
        <div className="max-w-7xl mx-auto">
          <SearchPage />
        </div>
      </main>
      <BottomNav />
    </>
  );
}
