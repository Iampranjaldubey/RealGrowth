/**
 * Sync a piece of state with a URL search parameter.
 *
 * The previous app kept every selection (year, country, tab) in local
 * `useState`, so nothing was shareable or bookmarkable and the back button did
 * nothing. Backing state with the URL fixes both for free.
 */

import { useCallback } from "react";
import { useSearchParams } from "react-router-dom";

export function useUrlState(key: string, defaultValue: string): [string, (value: string) => void] {
  const [searchParams, setSearchParams] = useSearchParams();
  const value = searchParams.get(key) ?? defaultValue;

  const setValue = useCallback(
    (next: string) => {
      setSearchParams(
        (previous) => {
          const params = new URLSearchParams(previous);
          if (next === defaultValue) {
            params.delete(key);
          } else {
            params.set(key, next);
          }
          return params;
        },
        { replace: true },
      );
    },
    [key, defaultValue, setSearchParams],
  );

  return [value, setValue];
}

export function useUrlNumberState(key: string, defaultValue: number): [number, (value: number) => void] {
  const [raw, setRaw] = useUrlState(key, String(defaultValue));
  const parsed = Number(raw);
  const value = Number.isFinite(parsed) ? parsed : defaultValue;
  const setValue = useCallback((next: number) => setRaw(String(next)), [setRaw]);
  return [value, setValue];
}
