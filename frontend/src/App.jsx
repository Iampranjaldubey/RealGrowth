import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import ErrorBoundary from './components/UI/ErrorBoundary';
import Navbar from './components/Layout/Navbar';

// Pages
import Home from './pages/Home';
import GDP from './pages/GDP';
import Inflation from './pages/Inflation';
import FoodPrices from './pages/FoodPrices';
import Population from './pages/Population';
import Wages from './pages/Wages';
import Debt from './pages/Debt';
import Growth from './pages/Growth';
import Correlation from './pages/Correlation';

const App = () => {
  return (
    <ThemeProvider>
      <Router>
        <div className="app-layout">
          <Navbar />
          
          <main className="main-content">
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/correlation" element={<Correlation />} />
                <Route path="/gdp" element={<GDP />} />
                <Route path="/inflation" element={<Inflation />} />
                <Route path="/food" element={<FoodPrices />} />
                <Route path="/population" element={<Population />} />
                <Route path="/wages" element={<Wages />} />
                <Route path="/debt" element={<Debt />} />
                <Route path="/growth" element={<Growth />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ErrorBoundary>
          </main>
        </div>
      </Router>
    </ThemeProvider>
  );
};

export default App;
