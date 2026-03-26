import { useState } from "react";
import { useNavigate } from "react-router-dom";
import BottomNav from "../components/BottomNav";
import TopNav from "../components/TopNav";
import { useUserId } from "../hooks/useUserId";

export default function Home() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const { userId } = useUserId();
  const [strategy, setStrategy] = useState("hybrid");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) navigate(`/search?q=${encodeURIComponent(query.trim())}`);
  };

  const handleRecs = (e: React.FormEvent) => {
    e.preventDefault();
    navigate(`/recommendations?user=${userId}&strategy=${strategy}`);
  };

  return (
    <>
      <TopNav />
      <main className="pt-20">
        {/* Hero Section */}
        <section className="relative h-[870px] flex flex-col items-center justify-center px-6 overflow-hidden">
          <div className="absolute inset-0 z-0">
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/60 to-background" />
            <div className="w-full h-full bg-surface-container-lowest opacity-30" />
          </div>
          <div className="relative z-10 text-center max-w-4xl space-y-8">
            <h1 className="font-headline text-6xl md:text-8xl font-extrabold tracking-tighter text-on-surface">
              CineMatch-AI
            </h1>
            <p className="font-headline text-xl md:text-2xl text-on-surface-variant font-medium tracking-tight">
              Discover your next favorite movie
            </p>
            {/* Search Bar */}
            <form
              onSubmit={handleSearch}
              className="w-full max-w-2xl mx-auto mt-12 relative group"
            >
              <div className="absolute inset-y-0 left-6 flex items-center pointer-events-none">
                <span className="material-symbols-outlined text-outline">search</span>
              </div>
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                className="w-full h-16 pl-16 pr-6 bg-surface-container-lowest border-none rounded-xl text-on-surface placeholder:text-outline/60 focus:ring-2 focus:ring-surface-tint shadow-2xl transition-all duration-300 font-body text-lg"
                placeholder="Search for titles, directors, or genres..."
                type="text"
              />
            </form>
          </div>
        </section>

        {/* Recommendations Section */}
        <section className="max-w-7xl mx-auto px-6 pb-32">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-start">
            {/* Control Panel */}
            <div className="lg:col-span-5 glass-panel p-10 rounded-2xl border border-outline-variant/10 space-y-10">
              <div className="space-y-2">
                <h2 className="font-headline text-3xl font-bold text-on-surface">
                  Get Recommendations
                </h2>
                <p className="font-body text-on-surface-variant">
                  Personalized curation powered by neural engines.
                </p>
              </div>
              <form onSubmit={handleRecs} className="space-y-8">
                <div className="space-y-3">
                  <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                    Member ID
                  </label>
                  <div className="relative glowing-border rounded-lg">
                    <div className="w-full bg-surface-container-lowest rounded-lg p-4 text-on-surface font-mono">
                      USR-{userId}
                    </div>
                  </div>
                </div>
                <div className="space-y-3">
                  <label className="block font-label text-xs uppercase tracking-widest text-on-surface-variant font-bold">
                    Discovery Engine
                  </label>
                  <div className="relative">
                    <select
                      value={strategy}
                      onChange={(e) => setStrategy(e.target.value)}
                      className="w-full bg-surface-container-lowest border-none rounded-lg p-4 text-on-surface appearance-none focus:ring-2 focus:ring-surface-tint font-body"
                    >
                      <option value="hybrid">Hybrid (Balanced)</option>
                      <option value="content">Content Based (Genre Focus)</option>
                      <option value="collab">Collaborative (Peer Trends)</option>
                    </select>
                    <div className="absolute inset-y-0 right-4 flex items-center pointer-events-none">
                      <span className="material-symbols-outlined text-outline">
                        expand_more
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  type="submit"
                  className="w-full py-5 bg-gradient-to-r from-primary to-primary-fixed-dim text-on-primary-container font-headline font-extrabold text-lg rounded-lg shadow-[0_0_30px_rgba(255,193,7,0.2)] hover:shadow-[0_0_45px_rgba(255,193,7,0.4)] transition-all duration-300 active:scale-[0.98]"
                >
                  GET RECOMMENDATIONS
                </button>
              </form>
            </div>
            {/* Editorial Visual */}
            <div className="lg:col-span-7 grid grid-cols-2 gap-4 h-full">
              <div className="space-y-4 pt-12">
                <div className="aspect-[2/3] rounded-xl overflow-hidden bg-surface-container shadow-2xl relative">
                  <div className="w-full h-full bg-gradient-to-br from-surface-container-highest to-surface-container flex items-center justify-center">
                    <span className="material-symbols-outlined text-6xl text-outline/30">movie</span>
                  </div>
                </div>
              </div>
              <div className="space-y-4">
                <div className="aspect-[2/3] rounded-xl overflow-hidden bg-surface-container shadow-2xl relative">
                  <div className="w-full h-full bg-gradient-to-br from-surface-container to-surface-container-low flex items-center justify-center">
                    <span className="material-symbols-outlined text-6xl text-outline/30">theaters</span>
                  </div>
                </div>
                <div className="aspect-[16/9] rounded-xl overflow-hidden bg-surface-container border border-outline-variant/10 p-6 flex flex-col justify-end">
                  <h3 className="font-headline font-bold text-lg">Curated Collections</h3>
                  <p className="text-sm text-on-surface-variant font-body">
                    Exclusive member-only premieres weekly.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
      <BottomNav />
    </>
  );
}
