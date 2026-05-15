"""Public listing of the bundled named-time-period gazetteer (issue #112).

``period_gazetteer.list_periods`` and the ``--list-periods`` CLI flag give
downstream tools (UIs, autocomplete widgets, reference docs) machine-
readable access to every period geoextent recognises, plus the licensing
and provenance metadata that ships with the data.
"""

import json

from geoextent.lib import period_gazetteer


def test_list_periods_returns_metadata_and_periods():
    data = period_gazetteer.list_periods()
    # Provenance / licensing block.
    for key in (
        "name",
        "schema_version",
        "source",
        "source_url",
        "source_revision",
        "license",
        "license_url",
        "attribution",
        "built_at",
        "ma_bp_origin_year",
        "period_count",
    ):
        assert key in data, f"missing metadata key: {key}"

    # ICS GTS2020 ships 178 units; assert >100 so the test doesn't break if
    # the upstream chart adds or removes a few entries on the next refresh.
    assert data["period_count"] >= 100
    assert data["period_count"] == len(data["periods"])
    # Schema version is a non-empty string we can compare against.
    assert isinstance(data["schema_version"], str) and data["schema_version"]
    # Built-at is an ISO-8601 UTC string ending in Z.
    assert data["built_at"].endswith("Z")
    # Licence is CC0 (ICS chart is public domain).
    assert data["license"] == "CC0-1.0"


def test_list_periods_name_filter_substring_match():
    data = period_gazetteer.list_periods(name_filter="holo")
    names = [p["name"] for p in data["periods"]]
    assert "Holocene" in names
    # The filter is a substring on name *or* alias — Holocene's alias is
    # "Holocene Epoch", so the match still hits.
    for rec in data["periods"]:
        haystack = (
            rec["name"].lower()
            + " "
            + " ".join(a.lower() for a in rec.get("aliases", []))
        )
        assert "holo" in haystack


def test_list_periods_filter_returns_empty_for_no_match():
    data = period_gazetteer.list_periods(name_filter="zzznotapenriod")
    assert data["periods"] == []
    assert data["period_count"] == 0


def test_list_periods_without_metadata():
    data = period_gazetteer.list_periods(include_metadata=False)
    assert set(data.keys()) == {"periods", "period_count"}


def test_each_period_has_required_fields():
    data = period_gazetteer.list_periods()
    for rec in data["periods"]:
        for key in ("name", "start", "end", "id", "url"):
            assert key in rec, f"period {rec!r} missing {key}"
        # Aliases and rank are optional but present in the ICS build.
        assert isinstance(rec.get("aliases", []), list)


def test_cli_list_periods_json(script_runner):
    ret = script_runner.run(["geoextent", "--list-periods"])
    assert ret.success, ret.stderr
    payload = json.loads(ret.stdout)
    assert payload["period_count"] == len(payload["periods"])
    assert payload["license"] == "CC0-1.0"


def test_cli_list_periods_text(script_runner):
    ret = script_runner.run(
        ["geoextent", "--list-periods", "--list-periods-format", "text"]
    )
    assert ret.success, ret.stderr
    out = ret.stdout
    # Header comments include the source URL and the licence.
    assert "ICS International Chronostratigraphic Chart" in out
    assert "License: CC0-1.0" in out
    # Tab-separated body rows.
    assert "\tEpoch\t" in out
    assert "Holocene\t" in out


def test_cli_list_periods_filter(script_runner):
    ret = script_runner.run(
        [
            "geoextent",
            "--list-periods",
            "--list-periods-filter",
            "Mesozoic",
        ]
    )
    assert ret.success, ret.stderr
    payload = json.loads(ret.stdout)
    names = [p["name"] for p in payload["periods"]]
    assert "Mesozoic" in names
    # Filter is narrow enough that the count is single digits.
    assert payload["period_count"] < 10
