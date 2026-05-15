"""Shared helpers and a deterministic fake gazetteer for text NER tests."""

import pytest

FAKE_DB = {
    "berlin": (52.52, 13.405),
    "paris": (48.8566, 2.3522),
    "tokyo": (35.6762, 139.6503),
    "london": (51.5072, -0.1276),
    "new york": (40.7128, -74.006),
    "germany": (51.1657, 10.4515),
    "france": (46.6034, 1.8883),
    "saxony": (51.05, 13.74),
    "bavaria": (48.7904, 11.4979),
    "brandenburg": (52.4125, 12.5316),
    "münchen": (48.1351, 11.582),
    "munich": (48.1351, 11.582),
    "são paulo": (-23.5505, -46.6333),
    "zürich": (47.3769, 8.5417),
    "springfield": [(39.7817, -89.6501), (37.215, -93.298)],
    # Extras for the text-plus-file merge regression test, so the
    # example in the howto / README runs deterministically in CI.
    "denmark": (56.2639, 9.5018),
    "belgium": (50.5039, 4.4699),
    "reykjavik": (64.1466, -21.9426),
}

# Subset of fixtures that the fake Nominatim-style backend returns with an
# admin boundary polygon, so tests can exercise the boundary path. The
# polygon is a tiny synthetic square around the point so envelope checks
# remain deterministic.
FAKE_BOUNDARIES = {
    "saxony": {
        "type": "Polygon",
        "coordinates": [
            [
                [11.87, 50.17],
                [15.04, 50.17],
                [15.04, 51.69],
                [11.87, 51.69],
                [11.87, 50.17],
            ]
        ],
    },
}


def fake_geocode(self, query, limit=5):
    key = query.strip().lower()
    if key not in FAKE_DB:
        return []
    val = FAKE_DB[key]
    boundary = FAKE_BOUNDARIES.get(key)
    if isinstance(val, list):
        return [
            {
                "name": query,
                "lat": lat,
                "lon": lon,
                "id": f"fake:{key}:{i}",
                "url": f"https://example.invalid/{key}/{i}",
                "boundary": boundary if i == 0 else None,
            }
            for i, (lat, lon) in enumerate(val)
        ]
    lat, lon = val
    return [
        {
            "name": query,
            "lat": lat,
            "lon": lon,
            "id": f"fake:{key}",
            "url": f"https://example.invalid/{key}",
            "boundary": boundary,
        }
    ]


def install_fake_gazetteer(monkeypatch):
    """Patch every gazetteer service's geocode to use FAKE_DB."""
    from geoextent.lib import gazetteer

    for cls in (
        gazetteer.GeoNamesService,
        gazetteer.NominatimService,
        gazetteer.PhotonService,
    ):
        monkeypatch.setattr(cls, "geocode", fake_geocode, raising=True)
    monkeypatch.setenv("GEONAMES_USERNAME", "test")
