import { NavLink, Route, HashRouter as Router, Routes } from "react-router-dom";
import { DemoTag } from "./components/ui";
import Overview from "./pages/Overview";
import MapPage from "./pages/MapPage";
import Bins from "./pages/Bins";
import Planner from "./pages/Planner";
import Fleet from "./pages/Fleet";
import Recycling from "./pages/Recycling";
import Forecasts from "./pages/Forecasts";
import Agents from "./pages/Agents";
import Alerts from "./pages/Alerts";
import SettingsPage from "./pages/Settings";

const NAV = [
  { to: "/", label: "Overview", icon: "▦", end: true },
  { to: "/map", label: "Live Map", icon: "◎" },
  { to: "/bins", label: "Bins & Sensors", icon: "▤" },
  { to: "/planner", label: "Collection Planner", icon: "➤" },
  { to: "/fleet", label: "Fleet & Fuel", icon: "⛟" },
  { to: "/recycling", label: "Recycling", icon: "♻" },
  { to: "/forecasts", label: "Forecasts", icon: "◠" },
  { to: "/agents", label: "Agent Activity", icon: "⬡" },
  { to: "/alerts", label: "Alerts", icon: "⚠" },
  { to: "/settings", label: "Settings", icon: "⚙" },
];

export default function App() {
  return (
    <Router>
      <div className="flex min-h-screen">
        {/* ── sidebar ── */}
        <aside className="sticky top-0 hidden h-screen w-60 shrink-0 flex-col border-r border-edge bg-panel/60 backdrop-blur md:flex">
          <div className="flex items-center gap-2.5 px-5 py-5">
            <span className="flex size-9 items-center justify-center rounded-xl bg-lime text-lg text-white">
              ♻
            </span>
            <div>
              <p className="text-base font-extrabold tracking-tight text-ink">WasteWise</p>
              <p className="text-[10px] uppercase tracking-widest text-dim">Control Tower</p>
            </div>
          </div>

          <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-2">
            {NAV.map((n) => (
              <NavLink
                key={n.to}
                to={n.to}
                end={n.end}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${
                    isActive
                      ? "bg-lime/15 font-semibold text-lime"
                      : "text-dim hover:bg-panel2 hover:text-ink"
                  }`
                }
              >
                <span className="w-4 text-center text-xs">{n.icon}</span>
                {n.label}
              </NavLink>
            ))}
          </nav>

          <div className="space-y-2 border-t border-edge/60 px-4 py-4">
            <DemoTag>Demo · Simulated data</DemoTag>
            <p className="text-[10px] leading-relaxed text-dim/70">
              Multi-agent workflow: LangGraph + OR-Tools. All telemetry is synthetic and labelled.
            </p>
          </div>
        </aside>

        {/* ── main ── */}
        <div className="flex min-w-0 flex-1 flex-col">
          {/* mobile nav */}
          <div className="sticky top-0 z-40 border-b border-edge bg-abyss/90 backdrop-blur md:hidden">
            <div className="flex items-center justify-between px-4 py-3">
              <p className="flex items-center gap-2 font-extrabold text-ink">
                <span className="flex size-7 items-center justify-center rounded-lg bg-lime text-white">♻</span>
                WasteWise
              </p>
              <DemoTag>Demo</DemoTag>
            </div>
            <div className="flex gap-1 overflow-x-auto px-2 pb-2">
              {NAV.map((n) => (
                <NavLink
                  key={n.to}
                  to={n.to}
                  end={n.end}
                  className={({ isActive }) =>
                    `whitespace-nowrap rounded-full px-3 py-1.5 text-xs ${
                      isActive ? "bg-lime/20 font-semibold text-lime" : "text-dim"
                    }`
                  }
                >
                  {n.label}
                </NavLink>
              ))}
            </div>
          </div>

          <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-6 sm:px-6 lg:px-8">
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/map" element={<MapPage />} />
              <Route path="/bins" element={<Bins />} />
              <Route path="/planner" element={<Planner />} />
              <Route path="/fleet" element={<Fleet />} />
              <Route path="/recycling" element={<Recycling />} />
              <Route path="/forecasts" element={<Forecasts />} />
              <Route path="/agents" element={<Agents />} />
              <Route path="/alerts" element={<Alerts />} />
              <Route path="/settings" element={<SettingsPage />} />
              <Route path="*" element={<Overview />} />
            </Routes>
          </main>

          <footer className="border-t border-edge/50 px-6 py-4 text-center text-[11px] text-dim/60">
            WasteWise · AI-Powered Waste Management · multi-agent demo · data is simulated and labelled
          </footer>
        </div>
      </div>
    </Router>
  );
}
