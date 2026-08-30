import type { ReactNode } from "react";
import { ChartSkeleton } from "./Skeleton";

interface ChartCardProps {
  title?: string;
  subtitle?: string;
  loading?: boolean;
  error?: string | null;
  children?: ReactNode;
}

export function ChartCard({ title, subtitle, loading = false, error = null, children }: ChartCardProps) {
  if (error) {
    return (
      <div className="glass-card glass-card--center" style={{ minHeight: 300 }}>
        <div style={{ fontSize: 24 }}>⚠️</div>
        <p>Failed to load chart data.</p>
        <small style={{ color: "var(--text-tertiary)" }}>{error}</small>
      </div>
    );
  }

  if (loading) {
    return <ChartSkeleton />;
  }

  return (
    <div className="glass-card animate-fade-in-up" style={{ display: "flex", flexDirection: "column" }}>
      {(title || subtitle) && (
        <div style={{ marginBottom: 16 }}>
          {title && <h3 style={{ fontSize: "1.2rem", marginBottom: 4 }}>{title}</h3>}
          {subtitle && <p style={{ fontSize: "0.85rem" }}>{subtitle}</p>}
        </div>
      )}
      <div style={{ flex: 1, position: "relative" }}>{children}</div>
    </div>
  );
}
