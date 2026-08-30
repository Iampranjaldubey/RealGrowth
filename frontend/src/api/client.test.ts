import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "./client";

const originalFetch = globalThis.fetch;

function mockFetch(response: unknown): ReturnType<typeof vi.fn> {
  const fetchMock = vi.fn().mockResolvedValue(response);
  globalThis.fetch = fetchMock as unknown as typeof fetch;
  return fetchMock;
}

describe("api client", () => {
  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("escapes path segments so special characters can't break the URL", async () => {
    const fetchMock = mockFetch({ ok: true, json: async () => ({ id: "x" }) });

    await api.getIndicator("weird/id?x=1");

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining("weird%2Fid%3Fx%3D1"),
      expect.anything(),
    );
  });

  it("omits undefined/null/empty query parameters", async () => {
    const fetchMock = mockFetch({ ok: true, json: async () => ({ series: [] }) });

    await api.getSeries("gdp_per_capita", ["USA"], {});

    const calledUrl = fetchMock.mock.calls[0]?.[0] as string;
    expect(calledUrl).not.toContain("start_year");
    expect(calledUrl).not.toContain("end_year");
    expect(calledUrl).toContain("countries=USA");
  });

  it("throws a typed ApiError carrying the backend error contract", async () => {
    mockFetch({
      ok: false,
      status: 404,
      statusText: "Not Found",
      json: async () => ({ error: "Not found", detail: "unknown country: ZZZ", status: 404 }),
    });

    await expect(api.getCountryProfile("ZZZ")).rejects.toMatchObject({
      name: "ApiError",
      status: 404,
      detail: "unknown country: ZZZ",
    });
  });

  it("ApiError is an instance of Error", () => {
    const error = new ApiError({ error: "boom", detail: null, status: 500 });
    expect(error).toBeInstanceOf(Error);
    expect(error.message).toBe("boom");
  });

  it("requests are made relative to /api by default in tests", async () => {
    const fetchMock = mockFetch({ ok: true, json: async () => [] });
    await api.listIndicators();
    const calledUrl = fetchMock.mock.calls[0]?.[0] as string;
    expect(calledUrl.startsWith("/api")).toBe(true);
  });
});
