import type { CSSProperties } from "react";
import { StatCardSkeleton } from "./Skeleton";

interface Trend {
  value: number;
  isPositive: boolean;
}

interface StatCardProps {
  title: string;
  value: string;
  icon?: string;
  color?: "primary" | "secondary" | "tertiary" | "warning" | "danger";
  trend?: Trend;
  loading?: boolean;
}

/**
 * Unlike the previous StatCard, this takes an already-formatted string value
 * rather than animating a raw number with `setInterval` — the animation added
 * complexity without changing what information the card conveys, and it
 * fought with the "N/A" formatting path.
 */
export function StatCard({ title, value, icon, color = "primary", trend, loading = false }: StatCardProps) {
  if (loading) {
    return <StatCardSkeleton />;
  }

  return (
    <div className="glass-card stat-card animate-fade-in-up" style={{ "--stat-color": `var(--accent-${color})` } as CSSProperties}>
      <div className="stat-card__header">
        <h4 className="stat-card__title">{title}</h4>
        {icon && <span aria-hidden="true">{icon}</span>}
      </div>
      <span className="stat-card__value">{value}</span>
      {trend && (
        <div className={`stat-card__trend ${trend.isPositive ? "stat-card__trend--up" : "stat-card__trend--down"}`}>
          {trend.isPositive ? "↑" : "↓"} {Math.abs(trend.value)}%
        </div>
      )}
    </div>
  );
}
