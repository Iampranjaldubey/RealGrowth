import React, { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import { useTheme } from '../../context/ThemeContext';
import './Navbar.css';

const navLinks = [
  { path: '/', label: 'Dashboard', icon: '📊' },
  { path: '/correlation', label: 'Correlation', icon: '🔬', highlight: true },
  { path: '/gdp', label: 'GDP Per Capita', icon: '💰' },
  { path: '/inflation', label: 'Inflation', icon: '📈' },
  { path: '/food', label: 'Food Prices', icon: '🍲' },
  { path: '/population', label: 'Population', icon: '👥' },
  { path: '/wages', label: 'Average Wages', icon: '💵' },
  { path: '/debt', label: 'Debt to GDP', icon: '🏦' },
  { path: '/growth', label: 'Real Growth', icon: '🚀' },
];

const Navbar = () => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();

  // Close mobile menu on route change
  useEffect(() => {
    setIsMobileOpen(false);
  }, [location.pathname]);

  return (
    <>
      <button 
        className="mobile-toggle"
        onClick={() => setIsMobileOpen(true)}
      >
        ☰
      </button>

      <div 
        className={`sidebar-overlay ${isMobileOpen ? 'visible' : ''}`}
        onClick={() => setIsMobileOpen(false)}
      />

      <aside className={`sidebar ${isCollapsed ? 'collapsed' : ''} ${isMobileOpen ? 'mobile-open' : ''}`}>
        <div className="sidebar-header">
          <h2>RealGrowth</h2>
          <button 
            className="toggle-btn"
            onClick={() => setIsCollapsed(!isCollapsed)}
            title={isCollapsed ? "Expand" : "Collapse"}
          >
            {isCollapsed ? '»' : '«'}
          </button>
        </div>

        <nav className="sidebar-nav">
          {navLinks.map((link) => (
            <NavLink
              key={link.path}
              to={link.path}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <span className="nav-icon">{link.icon}</span>
              <span className="nav-label">
                {link.label}
                {link.highlight && (
                  <span style={{ 
                    fontSize: '0.65rem', 
                    background: 'var(--accent-gradient)', 
                    padding: '2px 6px', 
                    borderRadius: '10px', 
                    marginLeft: '8px',
                    color: 'white'
                  }}>
                    NEW
                  </span>
                )}
              </span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <button 
            className="btn-icon" 
            onClick={toggleTheme}
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </div>
      </aside>
    </>
  );
};

export default Navbar;
