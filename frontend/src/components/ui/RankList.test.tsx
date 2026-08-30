import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RankList } from "./RankList";
import type { SnapshotValue } from "@/types/api";

const values: SnapshotValue[] = [
  { iso3: "USA", country: "United States", region: "North America", value: 80000 },
  { iso3: "IND", country: "India", region: "South Asia", value: 2500 },
];

describe("RankList", () => {
  it("renders one row per value, in the order given", () => {
    render(<RankList values={values} unitSymbol="$" decimals={0} />);
    const names = screen.getAllByText(/United States|India/);
    expect(names.map((n) => n.textContent)).toEqual(["United States", "India"]);
  });

  it("respects the limit prop", () => {
    render(<RankList values={values} unitSymbol="$" decimals={0} limit={1} />);
    expect(screen.queryByText("India")).not.toBeInTheDocument();
  });

  it("formats each value using the given unit", () => {
    render(<RankList values={values} unitSymbol="$" decimals={0} />);
    expect(screen.getByText("$80,000")).toBeInTheDocument();
  });
});
