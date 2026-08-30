import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { ThemeProvider } from "@/context/ThemeContext";
import { ErrorBoundary } from "@/components/ui/ErrorBoundary";
import { Sidebar } from "@/components/layout/Sidebar";
import { HomePage } from "@/pages/HomePage";
import { IndicatorExplorerPage } from "@/pages/IndicatorExplorerPage";
import { CorrelationPage } from "@/pages/CorrelationPage";
import { DataQualityPage } from "@/pages/DataQualityPage";

export function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <div className="app-layout">
          <Sidebar />
          <main className="main-content">
            <ErrorBoundary>
              <Routes>
                <Route path="/" element={<HomePage />} />
                <Route path="/correlation" element={<CorrelationPage />} />
                <Route path="/data-quality" element={<DataQualityPage />} />
                <Route path="/indicators/:indicatorId" element={<IndicatorExplorerPage />} />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ErrorBoundary>
          </main>
        </div>
      </BrowserRouter>
    </ThemeProvider>
  );
}
