import { describe, expect, it } from "vitest";
import { formatByUnit, formatCompactNumber, formatCurrency, formatNumber, formatPercent } from "./formatters";

describe("formatCurrency", () => {
  it("formats a positive value as USD", () => {
    expect(formatCurrency(1234)).toBe("$1,234");
  });

  it("respects the decimals argument", () => {
    expect(formatCurrency(1234.5, 2)).toBe("$1,234.50");
  });

  it.each([null, undefined, NaN, Infinity, -Infinity])("returns N/A for %p", (value) => {
    expect(formatCurrency(value as number)).toBe("N/A");
  });
});

describe("formatPercent", () => {
  it("appends a percent sign", () => {
    expect(formatPercent(5.5)).toBe("+5.50%");
  });

  it("shows a sign for negative values", () => {
    expect(formatPercent(-3.2)).toBe("-3.20%");
  });

  it("returns N/A for missing values", () => {
    expect(formatPercent(undefined)).toBe("N/A");
  });
});

describe("formatCompactNumber", () => {
  it("abbreviates large numbers", () => {
    expect(formatCompactNumber(1_500_000)).toBe("1.5M");
  });

  it("returns N/A for non-finite input", () => {
    expect(formatCompactNumber(Infinity)).toBe("N/A");
  });
});

describe("formatNumber", () => {
  it("adds thousands separators", () => {
    expect(formatNumber(1234567)).toBe("1,234,567");
  });
});

describe("formatByUnit", () => {
  it("prefixes currency symbol", () => {
    expect(formatByUnit(500, "$", 0)).toBe("$500");
  });

  it("suffixes percent symbol", () => {
    expect(formatByUnit(12.5, "%", 1)).toBe("12.5%");
  });

  it("returns the plain number for no unit", () => {
    expect(formatByUnit(1000, "", 0)).toBe("1,000");
  });

  it("returns N/A for missing values regardless of unit", () => {
    expect(formatByUnit(null, "$", 0)).toBe("N/A");
  });
});
