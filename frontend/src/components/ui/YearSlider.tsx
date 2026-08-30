interface YearSliderProps {
  min: number;
  max: number;
  value: number;
  onChange: (year: number) => void;
  label?: string;
}

/**
 * The previous version of this component was reused across pages but each
 * page passed its own hardcoded `min`/`max`, which is what let Debt.jsx offer
 * years 1950-2022 against a dataset covering only 2018-2022. Callers now pass
 * an indicator's real `min_year`/`max_year` from the API (see
 * IndicatorExplorerPage), so a bad range is a data problem, not a UI one.
 */
export function YearSlider({ min, max, value, onChange, label = "Year" }: YearSliderProps) {
  return (
    <div className="form-group" style={{ minWidth: 220 }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <label htmlFor="year-slider">{label}</label>
        <span style={{ fontWeight: 700, color: "var(--accent-primary)", fontVariantNumeric: "tabular-nums" }}>
          {value}
        </span>
      </div>
      <input
        id="year-slider"
        type="range"
        min={min}
        max={max}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        aria-valuemin={min}
        aria-valuemax={max}
        aria-valuenow={value}
      />
      <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-tertiary)", fontSize: "0.75rem" }}>
        <span>{min}</span>
        <span>{max}</span>
      </div>
    </div>
  );
}
