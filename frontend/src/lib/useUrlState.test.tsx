import type { ReactNode } from "react";
import { act, renderHook } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { useUrlNumberState, useUrlState } from "./useUrlState";

function withRouter(initialEntries: string[] = ["/"]) {
  return ({ children }: { children: ReactNode }) => (
    <MemoryRouter initialEntries={initialEntries}>{children}</MemoryRouter>
  );
}

describe("useUrlState", () => {
  it("defaults to the provided value when the param is absent", () => {
    const { result } = renderHook(() => useUrlState("year", "2022"), { wrapper: withRouter() });
    expect(result.current[0]).toBe("2022");
  });

  it("reads an existing param from the URL", () => {
    const { result } = renderHook(() => useUrlState("country", "USA"), {
      wrapper: withRouter(["/?country=IND"]),
    });
    expect(result.current[0]).toBe("IND");
  });

  it("updates the value when setValue is called", () => {
    const { result } = renderHook(() => useUrlState("country", "USA"), { wrapper: withRouter() });
    act(() => result.current[1]("DEU"));
    expect(result.current[0]).toBe("DEU");
  });

  it("removes the param entirely when set back to the default", () => {
    const { result } = renderHook(() => useUrlState("country", "USA"), {
      wrapper: withRouter(["/?country=IND"]),
    });
    act(() => result.current[1]("USA"));
    expect(result.current[0]).toBe("USA");
  });
});

describe("useUrlNumberState", () => {
  it("parses a numeric param", () => {
    const { result } = renderHook(() => useUrlNumberState("year", 2020), {
      wrapper: withRouter(["/?year=2015"]),
    });
    expect(result.current[0]).toBe(2015);
  });

  it("falls back to the default for a non-numeric param", () => {
    const { result } = renderHook(() => useUrlNumberState("year", 2020), {
      wrapper: withRouter(["/?year=notanumber"]),
    });
    expect(result.current[0]).toBe(2020);
  });

  it("updates as a number", () => {
    const { result } = renderHook(() => useUrlNumberState("year", 2020), { wrapper: withRouter() });
    act(() => result.current[1](2023));
    expect(result.current[0]).toBe(2023);
  });
});
