"""Ingestion: HTTP retries, the three connectors, and snapshot round-trips.

No test here touches the network. Each connector is fed a payload recorded
from (and trimmed down to) the real API's response shape, through
``HttpClient``'s injectable transport.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from realgrowth.ingest.catalog import ALL_SERIES, SeriesSpec, series_by_id
from realgrowth.ingest.connectors import (
    FetchResult,
    Row,
    fetch_imf,
    fetch_owid,
    fetch_worldbank,
)
from realgrowth.ingest.http import FetchError, HttpClient
from realgrowth.ingest.snapshot import (
    read_manifest,
    read_series,
    verify,
    write_manifest,
    write_series,
)

ALLOWED = {"USA", "IND", "XKX", "WLD", "AGG_AFE"}


class FakeTransport:
    """Replays queued ``(status, body)`` responses and records requested URLs."""

    def __init__(self, *responses: tuple[int, bytes]) -> None:
        self.responses = list(responses)
        self.urls: list[str] = []
        self.headers: list[dict[str, str]] = []

    def __call__(self, url: str, headers: dict[str, str], timeout: float) -> tuple[int, bytes]:
        self.urls.append(url)
        self.headers.append(headers)
        if not self.responses:
            raise AssertionError(f"unexpected request: {url}")
        return self.responses.pop(0)


def _client(*responses: tuple[int, bytes]) -> tuple[HttpClient, FakeTransport]:
    transport = FakeTransport(*responses)
    return HttpClient(transport=transport, sleep=lambda _: None), transport


def _json(payload: object) -> bytes:
    return json.dumps(payload).encode()


# ------------------------------------------------------------------- http


class TestHttpClient:
    def test_retries_transient_failures_then_succeeds(self) -> None:
        client, transport = _client((502, b""), (503, b""), (200, b'{"ok": true}'))
        assert client.get_json("https://example.test") == {"ok": True}
        assert len(transport.urls) == 3

    def test_does_not_retry_client_errors(self) -> None:
        client, transport = _client((404, b"nope"), (200, b"{}"))
        with pytest.raises(FetchError, match="permanently"):
            client.get_json("https://example.test")
        assert len(transport.urls) == 1

    def test_gives_up_after_max_attempts(self) -> None:
        client, _ = _client(*[(500, b"")] * 4)
        with pytest.raises(FetchError, match="after 4 attempts"):
            client.get_json("https://example.test")

    def test_backoff_is_exponential(self) -> None:
        delays: list[float] = []
        transport = FakeTransport((500, b""), (500, b""), (200, b"{}"))
        client = HttpClient(transport=transport, sleep=delays.append, backoff_seconds=1.0)
        client.get_json("https://example.test")
        assert delays == [1.0, 2.0]

    def test_sends_identifying_user_agent_and_json_accept(self) -> None:
        client, transport = _client((200, b"{}"))
        client.get_json("https://example.test")
        assert "RealGrowth" in transport.headers[0]["User-Agent"]
        assert transport.headers[0]["Accept"] == "application/json"

    def test_invalid_json_is_a_fetch_error(self) -> None:
        client, _ = _client((200, b"<html>"))
        with pytest.raises(FetchError, match="invalid JSON"):
            client.get_json("https://example.test")


# -------------------------------------------------------------- connectors


WB_SPEC = SeriesSpec("inflation_rate", "worldbank", "FP.CPI.TOTL.ZG")


def _wb_record(code: str, year: int, value: float | None) -> dict[str, object]:
    return {
        "indicator": {"id": "FP.CPI.TOTL.ZG", "value": "Inflation"},
        "country": {"id": "xx", "value": "x"},
        "countryiso3code": code,
        "date": str(year),
        "value": value,
    }


class TestWorldBank:
    def test_parses_filters_and_paginates(self) -> None:
        page1 = [
            {"page": 1, "pages": 2, "lastupdated": "2026-10-08"},
            [
                _wb_record("USA", 2024, 2.9),
                _wb_record("IND", 2024, None),  # no observation
                _wb_record("AFE", 2024, 4.1),  # aggregate -> AGG_AFE
                _wb_record("HIC", 2024, 3.0),  # aggregate the registry lacks
                _wb_record("", 2024, 1.0),  # malformed
            ],
        ]
        page2 = [{"page": 2, "pages": 2}, [_wb_record("IND", 2023, 5.6)]]
        client, transport = _client((200, _json(page1)), (200, _json(page2)))
        result = fetch_worldbank(WB_SPEC, client, ALLOWED, end_year=2025)

        assert result.rows == [
            Row("AGG_AFE", 2024, 4.1),
            Row("IND", 2023, 5.6),
            Row("USA", 2024, 2.9),
        ]
        assert result.dropped_codes == {"HIC"}
        assert result.source_last_updated == "2026-10-08"
        assert "date=1960:2025" in transport.urls[0]
        assert transport.urls[1].endswith("&page=2")

    def test_error_payload_raises(self) -> None:
        payload = [{"message": [{"id": "120", "value": "Invalid value"}]}]
        client, _ = _client((200, _json(payload)))
        with pytest.raises(FetchError, match="unexpected payload"):
            fetch_worldbank(WB_SPEC, client, ALLOWED)


class TestImf:
    PAYLOAD = {
        "values": {
            "PCPIPCH": {
                "USA": {"2024": 2.9, "2025": 2.7, "2026": 2.4, "2027": 2.1},
                "UVK": {"2025": 3.0, "2026": 2.0},  # IMF's code for Kosovo
                "WEOWORLD": {"2026": 3.9},
                "ADVEC": {"2026": 2.2},  # group, not a country
            }
        }
    }

    def test_projection_part_keeps_only_vintage_year_onwards(self) -> None:
        spec = SeriesSpec("f", "imf", "PCPIPCH", imf_part="projection")
        client, _ = _client((200, _json(self.PAYLOAD)))
        result = fetch_imf(spec, client, ALLOWED, vintage_year=2026)
        assert result.rows == [
            Row("USA", 2026, 2.4),
            Row("USA", 2027, 2.1),
            Row("WLD", 2026, 3.9),
            Row("XKX", 2026, 2.0),
        ]
        assert result.dropped_codes == {"ADVEC"}

    def test_history_part_drops_projections(self) -> None:
        spec = SeriesSpec("h", "imf", "PCPIPCH", imf_part="history")
        client, _ = _client((200, _json(self.PAYLOAD)))
        result = fetch_imf(spec, client, ALLOWED, vintage_year=2026)
        assert {r.year for r in result.rows} == {2024, 2025}

    def test_unexpected_shape_raises(self) -> None:
        spec = SeriesSpec("h", "imf", "PCPIPCH")
        client, _ = _client((200, _json({"values": {}})))
        with pytest.raises(FetchError, match="unexpected payload"):
            fetch_imf(spec, client, ALLOWED)


class TestOwid:
    def test_parses_csv_and_maps_world(self) -> None:
        body = (
            b"entity,code,year,cost_of_a_healthy_diet\n"
            b"United States,USA,2021,2.9\n"
            b"World,OWID_WRL,2021,3.6\n"
            b"Africa,,2021,4.0\n"
            b"India,IND,2021,\n"
        )
        client, _ = _client((200, body))
        result = fetch_owid(SeriesSpec("d", "owid", "cost-healthy-diet"), client, ALLOWED)
        assert result.rows == [Row("USA", 2021, 2.9), Row("WLD", 2021, 3.6)]
        assert result.dropped_codes == {"Africa"}

    def test_rejects_unexpected_header(self) -> None:
        client, _ = _client((200, b"a,b\n1,2\n"))
        with pytest.raises(FetchError, match="unexpected header"):
            fetch_owid(SeriesSpec("d", "owid", "x"), client, ALLOWED)


# --------------------------------------------------------------- snapshot


class TestSnapshot:
    def _result(self) -> FetchResult:
        return FetchResult(
            spec=WB_SPEC,
            url="https://api.worldbank.org/x",
            rows=[Row("IND", 2023, 5.649), Row("USA", 2024, 2.0)],
            fetched_at="2026-10-27T00:00:00+00:00",
            source_last_updated="2026-10-08",
        )

    def test_round_trips_exactly(self, tmp_path: Path) -> None:
        entry = write_series(tmp_path, self._result())
        assert read_series(tmp_path / "inflation_rate.csv") == self._result().rows
        assert entry.rows == 2 and entry.countries == 2
        assert (entry.min_year, entry.max_year) == (2023, 2024)

    def test_manifest_merges_and_verifies(self, tmp_path: Path) -> None:
        write_manifest(tmp_path, [write_series(tmp_path, self._result())])
        write_manifest(tmp_path, [])  # a partial refresh keeps earlier entries
        assert set(read_manifest(tmp_path)) == {"inflation_rate"}
        assert verify(tmp_path) == []

    def test_verify_detects_hand_edits(self, tmp_path: Path) -> None:
        write_manifest(tmp_path, [write_series(tmp_path, self._result())])
        path = tmp_path / "inflation_rate.csv"
        path.write_text(path.read_text() + "USA,2025,99\n")
        assert verify(tmp_path) == ["inflation_rate: sha256 mismatch (file edited after fetch?)"]


class TestCatalog:
    def test_ids_are_unique(self) -> None:
        assert len(series_by_id()) == len(ALL_SERIES)

    def test_every_snapshot_series_feeds_an_indicator_or_the_benchmark(self) -> None:
        from realgrowth.etl.sources import API_INDICATORS, IMF_FORECAST_SERIES

        assert set(series_by_id()) == set(API_INDICATORS) | {IMF_FORECAST_SERIES}

    def test_committed_snapshot_matches_its_manifest(self) -> None:
        from tests.conftest import RAW_DIR

        assert verify(RAW_DIR / "api") == []
