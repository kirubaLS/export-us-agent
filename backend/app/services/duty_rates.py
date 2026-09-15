"""Stub duty-rate lookup — stands in for the real Export-to-Entry Agent's
duty-research stage (Section 9.2). In production this calls out to a
tariff-schedule source (USITC HTS API / a licensed data provider) and
returns a cited, dated rate. Here it is a small fixture table so the
landed-cost pipeline, caching and API contract are all real; only the
data source is mocked.

Discipline preserved from the export agent spec: return None rather than
guess when a classification is not in the table — callers must render
'rate not available' rather than fabricate a number.
"""

from datetime import date

_FIXTURE_RATES: dict[str, dict] = {
    "6912.00.4810": {
        "ad_valorem_pct": 9.8,
        "source": "HTSUS 2026 Basic Edition, Chapter 69",
        "as_of": date(2026, 1, 1).isoformat(),
    },
    "6203.42.4011": {
        "ad_valorem_pct": 16.6,
        "source": "HTSUS 2026 Basic Edition, Chapter 62",
        "as_of": date(2026, 1, 1).isoformat(),
    },
    "9403.60.8081": {
        "ad_valorem_pct": 0.0,
        "source": "HTSUS 2026 Basic Edition, Chapter 94",
        "as_of": date(2026, 1, 1).isoformat(),
    },
}


def lookup_duty_rate(hts10: str, origin: str = "IN") -> dict | None:
    return _FIXTURE_RATES.get(hts10)
