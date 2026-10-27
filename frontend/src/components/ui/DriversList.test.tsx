import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DriversList } from "./DriversList";

describe("DriversList", () => {
  it("shows the largest drivers with direction and readable names", () => {
    render(
      <DriversList
        contributions={[
          { feature: "infl_lag0", feature_value: 1.2, contribution: 0.4 },
          { feature: "global_infl_change", feature_value: -0.1, contribution: -0.2 },
          { feature: "region_code", feature_value: 3, contribution: 0.01 },
        ]}
        limit={2}
      />,
    );
    const items = screen.getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(items[0]).toHaveTextContent("Inflation this year");
    expect(items[0]).toHaveTextContent("raises");
    expect(items[1]).toHaveTextContent("Change in global inflation");
    expect(items[1]).toHaveTextContent("lowers");
    expect(screen.queryByText("Region")).not.toBeInTheDocument();
  });

  it("explains an empty state", () => {
    render(<DriversList contributions={[]} />);
    expect(screen.getByText(/no attributions/i)).toBeInTheDocument();
  });
});
