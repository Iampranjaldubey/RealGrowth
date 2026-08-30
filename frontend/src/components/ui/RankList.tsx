import { formatByUnit } from "@/lib/formatters";
import type { SnapshotValue } from "@/types/api";

interface RankListProps {
  values: SnapshotValue[];
  unitSymbol: string;
  decimals: number;
  limit?: number;
}

/**
 * A ranked horizontal-bar list, standing in for a choropleth world map.
 *
 * The previous WorldMap loaded a TopoJSON file from a public CDN at runtime
 * (no offline fallback, no CSP allowance) via react-simple-maps, which does
 * not declare React 19 as a supported peer and only installs with
 * `--legacy-peer-deps`. It also joined data by English display name against
 * the map's own English names ("United States" vs "United States of
 * America"), so several major countries never rendered a value at all.
 *
 * A ranked list needs no map tiles, no geometry library, and communicates the
 * same "who's highest/lowest" question at least as clearly; the map itself
 * caused three of the resume-worthiness issues this rebuild fixes and is
 * intentionally not being re-added until it can be an ISO3-keyed SVG the app
 * ships itself.
 */
export function RankList({ values, unitSymbol, decimals, limit = 15 }: RankListProps) {
  const shown = values.slice(0, limit);
  const max = Math.max(...shown.map((v) => Math.abs(v.value)), 1);

  return (
    <div className="rank-list">
      {shown.map((entry, index) => (
        <div className="rank-row" key={entry.iso3}>
          <span className="rank-row__rank">{index + 1}</span>
          <span className="rank-row__name" title={entry.country}>
            {entry.country}
          </span>
          <div className="rank-row__bar-track">
            <div
              className="rank-row__bar-fill"
              style={{ width: `${Math.min(100, (Math.abs(entry.value) / max) * 100)}%` }}
            />
          </div>
          <span className="rank-row__value">{formatByUnit(entry.value, unitSymbol, decimals)}</span>
        </div>
      ))}
    </div>
  );
}
