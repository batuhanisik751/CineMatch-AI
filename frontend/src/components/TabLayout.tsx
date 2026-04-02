import { Link, Outlet, useLocation } from "react-router-dom";

interface Tab {
  label: string;
  icon: string;
  path: string;
}

interface TabLayoutProps {
  tabs: Tab[];
  baseRoute: string;
}

export default function TabLayout({ tabs, baseRoute }: TabLayoutProps) {
  const { pathname } = useLocation();

  return (
    <>
      <div className="hide-scrollbar overflow-x-auto border-b border-white/5 bg-[#1c1b1c]">
        <div className="flex gap-2 px-4 py-3">
          {tabs.map((tab) => {
            const to = `${baseRoute}/${tab.path}`;
            const active =
              pathname === to || pathname.startsWith(to + "/");
            return (
              <Link
                key={tab.path}
                to={to}
                className={
                  active
                    ? "flex items-center gap-2 whitespace-nowrap rounded-lg px-4 py-2.5 bg-[#FFC107] text-[#131314] shadow-[0_0_15px_rgba(255,193,7,0.3)] font-headline text-sm font-medium transition-all duration-200"
                    : "flex items-center gap-2 whitespace-nowrap rounded-lg px-4 py-2.5 text-[#d4c5ab] hover:bg-[#201f20] font-headline text-sm font-medium transition-all duration-200"
                }
              >
                <span
                  className="material-symbols-outlined text-[20px]"
                  style={
                    active
                      ? { fontVariationSettings: "'FILL' 1" }
                      : undefined
                  }
                >
                  {tab.icon}
                </span>
                {tab.label}
              </Link>
            );
          })}
        </div>
      </div>
      <Outlet />
    </>
  );
}
