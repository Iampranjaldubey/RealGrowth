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

interface NavSection {
  title: string;
  links: NavLinkItem[];
}

const NAV_SECTIONS: NavSection[] = [
  {
    title: "Overview",
    links: [{ path: "/", label: "Dashboard", icon: "📊" }],
  },
  {
    title: "Tools",
    links: [
      { path: "/forecasts", label: "Inflation Outlook", icon: "🔮", badge: "ML" },
      { path: "/purchasing-power", label: "Purchasing Power", icon: "🧮" },
      { path: "/correlation", label: "Correlation Explorer", icon: "🔬" },
    ],
  },
  {
    title: "Indicators",
    links: [
      { path: "/indicators/real_wage_growth", label: "Real Wage Growth", icon: "🚀" },
      { path: "/indicators/inflation_rate", label: "Inflation", icon: "📈" },
      { path: "/indicators/gdp_per_capita_ppp", label: "GDP Per Capita (PPP)", icon: "💰" },
      { path: "/indicators/gdp_growth", label: "GDP Growth", icon: "🏭" },
      { path: "/indicators/unemployment_rate", label: "Unemployment", icon: "👷" },
      { path: "/indicators/debt_to_gdp", label: "Government Debt", icon: "🏦" },
      { path: "/indicators/healthy_diet_cost", label: "Cost of a Healthy Diet", icon: "🍲" },
      { path: "/indicators/poverty_rate", label: "Extreme Poverty", icon: "🧭" },
      { path: "/indicators/population", label: "Population", icon: "👥" },
    ],
  },
  {
    title: "Transparency",
    links: [
      { path: "/models", label: "Models & Methodology", icon: "🧠" },
      { path: "/data-quality", label: "Data Quality", icon: "🔎" },
    ],
  },
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
          {NAV_SECTIONS.map((section) => (
            <div key={section.title} className="nav-section">
              <p className="nav-section__title">{section.title}</p>
              {section.links.map((link) => (
                <NavLink
                  key={link.path}
                  to={link.path}
                  end={link.path === "/"}
                  className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
                >
                  <span className="nav-icon" aria-hidden="true">
                    {link.icon}
                  </span>
                  <span>
                    {link.label}
                    {link.badge && (
                      <span className="badge badge--new" style={{ marginLeft: 8 }}>
                        {link.badge}
                      </span>
                    )}
                  </span>
                </NavLink>
              ))}
            </div>
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
