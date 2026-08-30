import { useCountries } from "@/api/queries";

interface CountrySelectProps {
  indicator?: string;
  value: string;
  onChange: (iso3: string) => void;
  label?: string;
  id: string;
}

/**
 * Restricts the option list to countries that actually have data for
 * `indicator` (when provided). The previous CountrySelector populated every
 * dropdown from the same unfiltered country list regardless of which chart it
 * fed, so selecting, e.g., a country absent from the debt dataset silently
 * rendered an empty chart.
 */
export function CountrySelect({ indicator, value, onChange, label = "Country", id }: CountrySelectProps) {
  const { data: countries, isLoading, isError } = useCountries({ indicator });

  return (
    <div className="form-group">
      {label && <label htmlFor={id}>{label}</label>}
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        disabled={isLoading || isError || !countries?.length}
      >
        <option value="">{isLoading ? "Loading…" : "Select a country"}</option>
        {countries?.map((country) => (
          <option key={country.iso3} value={country.iso3}>
            {country.name}
          </option>
        ))}
      </select>
      {isError && <small style={{ color: "var(--accent-danger)" }}>Failed to load countries</small>}
    </div>
  );
}
