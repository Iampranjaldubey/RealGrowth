import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatCard } from "./StatCard";

describe("StatCard", () => {
  it("renders the title and value", () => {
    render(<StatCard title="Avg GDP" value="$45,000" />);
    expect(screen.getByText("Avg GDP")).toBeInTheDocument();
    expect(screen.getByText("$45,000")).toBeInTheDocument();
  });

  it("renders a skeleton instead of content while loading", () => {
    render(<StatCard title="Avg GDP" value="$45,000" loading />);
    expect(screen.queryByText("$45,000")).not.toBeInTheDocument();
  });

  it("shows an upward trend indicator", () => {
    render(<StatCard title="Growth" value="5%" trend={{ value: 3, isPositive: true }} />);
    expect(screen.getByText("↑ 3%")).toBeInTheDocument();
  });

  it("shows a downward trend indicator", () => {
    render(<StatCard title="Growth" value="-5%" trend={{ value: 3, isPositive: false }} />);
    expect(screen.getByText("↓ 3%")).toBeInTheDocument();
  });
});
