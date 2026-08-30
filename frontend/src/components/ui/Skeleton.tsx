interface SkeletonProps {
  width?: string;
  height?: string;
  borderRadius?: string;
}

export function Skeleton({ width = "100%", height = "20px", borderRadius }: SkeletonProps) {
  return <div className="skeleton" style={{ width, height, borderRadius }} />;
}

export function ChartSkeleton() {
  return (
    <div className="glass-card" style={{ height: 380, display: "flex", flexDirection: "column", gap: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <Skeleton width="40%" height="26px" />
        <Skeleton width="120px" height="30px" />
      </div>
      <div style={{ flex: 1, display: "flex", alignItems: "flex-end", gap: "3%" }}>
        {Array.from({ length: 12 }, (_, i) => (
          <Skeleton key={i} width="7%" height={`${30 + ((i * 17) % 60)}%`} borderRadius="4px 4px 0 0" />
        ))}
      </div>
    </div>
  );
}

export function StatCardSkeleton() {
  return (
    <div className="glass-card">
      <Skeleton width="60%" height="18px" />
      <div style={{ height: 12 }} />
      <Skeleton width="80%" height="32px" />
    </div>
  );
}
