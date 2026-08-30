import { useEffect, useState } from "react";
import { NavLink, useLocation } from "react-router-dom";
import { useTheme } from "@/context/ThemeContext";
import "./Sidebar.css";

interface NavLinkItem {
  path: string;
  label: string;
  icon: string;
  badge?: string;
}

const NAV_LINKS: NavLinkItem[] = [
  { path: "/", label: "Dashboard", icon: "📊" },
  { path: "/correlation", label: "Correlation Explorer", icon: "🔬", badge: "NEW" },
  { path: "/indicators/real_wage_growth", label: "Real Wage Growth", icon: "🚀" },
  { path: "/indicators/gdp_per_capita", label: "GDP Per Capita", icon: "💰" },
  { path: "/indicators/inflation_rate", label: "Inflation", icon: "📈" },
  { path: "/indicators/avg_wage", label: "Average Wages", icon: "💵" },
  { path: "/indicators/debt_to_gdp", label: "Debt to GDP", icon: "🏦" },
  { path: "/indicators/healthy_diet_cost", label: "Cost of a Healthy Diet", icon: "🍲" },
  { path: "/indicators/population", label: "Population", icon: "👥" },
  { path: "/data-quality", label: "Data Quality", icon: "🔎" },
];

export function Sidebar() {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  useEffect(() => {
    setIsMobileOpen(false);
  }, [location.pathname]);

  return (
    <>
      <button
        type="button"
        className="mobile-toggle"
        onClick={() => setIsMobileOpen(true)}
        aria-label="Open navigation"
      >
        ☰
      </button>

      <div
        className={`sidebar-overlay ${isMobileOpen ? "visible" : ""}`}
        onClick={() => setIsMobileOpen(false)}
      />

      <aside className={`sidebar ${isMobileOpen ? "mobile-open" : ""}`}>
        <div className="sidebar-header">
          <h2>RealGrowth</h2>
        </div>

        <nav className="sidebar-nav" aria-label="Primary">
          {NAV_LINKS.map((link) => (
            <NavLink
              key={link.path}
              to={link.path}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <span className="nav-icon" aria-hidden="true">
                {link.icon}
              </span>
              <span>
                {link.label}
                {link.badge && <span className="badge badge--new" style={{ marginLeft: 8 }}>{link.badge}</span>}
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button
            type="button"
            className="btn-icon"
            onClick={toggleTheme}
            title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            aria-label="Toggle color theme"
          >
            {theme === "dark" ? "☀️" : "🌙"}
          </button>
        </div>
      </aside>
    </>
  );
}
