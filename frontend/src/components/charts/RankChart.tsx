import { Bar } from "react-chartjs-2";
import { baseOptions, paletteColor } from "@/lib/chartTheme";
import type { SnapshotValue } from "@/types/api";

interface RankChartProps {
  values: SnapshotValue[];
  valueFormatter?: (value: number) => string;
  limit?: number;
}

/** Horizontal ranked bar chart — used for "top N countries" snapshots. */
export function RankChart({ values, valueFormatter, limit = 10 }: RankChartProps) {
  const shown = values.slice(0, limit);

  return (
    <div className="chart-wrapper">
      <Bar
        data={{
          labels: shown.map((v) => v.country),
          datasets: [
            {
              label: "Value",
              data: shown.map((v) => v.value),
              backgroundColor: paletteColor(0),
              borderRadius: 4,
              borderSkipped: false,
            },
          ],
        }}
        options={baseOptions<"bar">({ valueFormatter, showLegend: false, indexAxis: "y" })}
      />
    </div>
  );
}
