/**
 * Number formatting helpers. Carried over from the previous
 * utils/formatters.js almost unchanged — it was the one genuinely clean,
 * reusable module in the old frontend — but typed and with an N/A guard that
 * also covers `Number.isFinite` (the original only checked `isNaN`, which
 * treats `Infinity` as valid).
 */

type Formattable = number | null | undefined;

function isFormattable(value: Formattable): value is number {
  return value !== null && value !== undefined && Number.isFinite(value);
}

export function formatCurrency(value: Formattable, decimals = 0): string {
  if (!isFormattable(value)) return "N/A";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPercent(value: Formattable, decimals = 2): string {
  if (!isFormattable(value)) return "N/A";
  return (
    new Intl.NumberFormat("en-US", {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
      signDisplay: "exceptZero",
    }).format(value) + "%"
  );
}

export function formatCompactNumber(value: Formattable): string {
  if (!isFormattable(value)) return "N/A";
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    compactDisplay: "short",
    maximumFractionDigits: 1,
  }).format(value);
}

export function formatNumber(value: Formattable, decimals = 0): string {
  if (!isFormattable(value)) return "N/A";
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/** Format a value using an indicator's own unit metadata. */
export function formatByUnit(value: Formattable, unitSymbol: string, decimals: number): string {
  if (!isFormattable(value)) return "N/A";
  const formatted = formatNumber(value, decimals);
  if (unitSymbol === "$") return `$${formatted}`;
  if (unitSymbol === "%") return `${formatted}%`;
  return formatted;
}
