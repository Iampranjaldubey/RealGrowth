"""Ingestion: fetch public statistical APIs into versioned on-disk snapshots.

Layout::

    http.py        urllib GET with retries/backoff and an injectable transport
    catalog.py     which series come from which API (World Bank, IMF, OWID)
    connectors.py  one fetcher per API, all returning (iso3, year, value) rows
    snapshot.py    long-format CSV + manifest.json with checksums
    __main__.py    ``python -m realgrowth.ingest``

Standard library only, like the ETL, so it runs in CI and on the deploy host
without the data-science stack.
"""
