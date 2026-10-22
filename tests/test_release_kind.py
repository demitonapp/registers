"""SM052 D5: a release's kinds are computed from the diff against the previous tag,
and a tag whose CHANGELOG section does not declare them is refused.

    python -m pytest tests/test_release_kind.py -q

The first three tests read real tags, so the checkout needs them (CI checks out
with fetch-depth 0). The rest use two-row trees, and the last group flattens fixture
instruments with `resolve.py`, so a version is named by the `in_force.from` the resolver
really writes (no real tag carries a dated row yet).
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import resolve  # noqa: E402
from release_kind import Tree, business_days_between, classify, computed_kinds, refusals, release_json, tree_at  # noqa: E402

V16_DATE = date(2026, 10, 12)  # v14, v15 and v16 were all tagged that day


@pytest.fixture(scope="module")
def tags() -> dict[str, Tree]:
    return {t: tree_at(t) for t in ("v13", "v14", "v15", "v16")}


def test_v13_to_v14_is_a_correction_only(tags) -> None:
    # Two NZ rows reworded (hswa_2015, nzs3910_2013); nothing added.
    assert computed_kinds(classify(tags["v13"], tags["v14"], V16_DATE)) == {"correction"}


def test_v14_to_v15_includes_an_addition(tags) -> None:
    changes = classify(tags["v14"], tags["v15"], V16_DATE)
    assert computed_kinds(changes) == {"addition", "correction"}
    assert {c.key for c in changes if c.kind == "addition"} == {
        r["key"] for i in tags["v15"].instruments if i["id"] == "tfnsw_c41" for r in i["obligations"]
    }
    # duty_shape added to every existing row is a changed field: a correction.
    assert sum(c.kind == "correction" for c in changes) == 428


def test_v15_to_v16_is_an_addition_only(tags) -> None:
    changes = classify(tags["v15"], tags["v16"], V16_DATE)
    assert computed_kinds(changes) == {"addition"}
    assert {"IE", "GB", "ZA", "CA", "GB-ENG", "CA-ON"} <= {c.key for c in changes}


TAG_DATE = date(2026, 11, 2)


def _tree(*rows: dict, instrument: str = "act", supported: tuple[str, ...] = ("AU",)) -> Tree:
    return Tree([{"id": instrument, "title": "An Act", "obligations": list(rows)}], frozenset(supported))


def _row(key: str = "a.b.c", **extra) -> dict:
    return {"key": key, "duty": "Give notice.", **extra}


def test_a_version_in_force_after_the_tag_is_an_amendment() -> None:
    old = _tree(_row())
    new = _tree(_row(in_force={"until": "2026-12-31"}), _row(duty="Give written notice.", in_force={"from": "2027-01-01"}))
    changes = classify(old, new, TAG_DATE)
    assert computed_kinds(changes) == {"amendment"}
    assert {c.commences for c in changes} == {date(2027, 1, 1)}


def test_a_version_in_force_on_or_before_the_tag_is_a_correction() -> None:
    old = _tree(_row())
    new = _tree(_row(in_force={"from": "2026-11-02"}))
    assert computed_kinds(classify(old, new, TAG_DATE)) == {"correction"}


def test_a_removed_key_is_a_correction_and_a_new_instrument_an_addition() -> None:
    old = _tree(_row("a.b.c"), _row("a.b.d"))
    new = Tree(_tree(_row("a.b.c")).instruments + _tree(_row("x.y.z"), instrument="new_act").instruments, frozenset({"AU"}))
    changes = classify(old, new, TAG_DATE)
    assert {(c.kind, c.key) for c in changes} == {("correction", "a.b.d"), ("addition", "x.y.z")}


def test_a_new_undated_key_in_an_existing_instrument_is_an_addition_its_author_may_call_a_correction() -> None:
    changes = classify(_tree(_row("a.b.c")), _tree(_row("a.b.c"), _row("a.b.d")), TAG_DATE)
    assert [(c.kind, c.alt) for c in changes] == [("addition", "correction")]
    assert refusals(changes, "## v17, 2026-11-02: correction\n", "v17", TAG_DATE) == []
    assert refusals(changes, "## v17, 2026-11-02: amendment\n", "v17", TAG_DATE) != []


def test_a_tag_must_declare_every_computed_kind() -> None:
    old = _tree(_row())
    new = Tree(_tree(_row(duty="Fixed.")).instruments + _tree(_row("x.y.z"), instrument="new_act").instruments, frozenset({"AU"}))
    changes = classify(old, new, TAG_DATE)
    assert refusals(changes, "# Changelog\n", "v17", TAG_DATE)  # no section at all
    assert refusals(changes, "## v17, 2026-10-14: correction\n", "v17", TAG_DATE)  # the addition undeclared
    good = "## v17, 2026-10-14: addition, correction\n"
    assert refusals(changes, good, "v17", date(2026, 10, 14)) == []
    assert release_json(changes, good, "v17") == {"tag": "v17", "kinds": ["addition", "correction"], "amendments": []}


def test_the_amendment_lead_counts_weekdays() -> None:
    # Monday 2 Nov to Monday 30 Nov 2026: four weeks, 20 weekdays.
    assert business_days_between(date(2026, 11, 2), date(2026, 11, 30)) == 20


# --- SM052 D1: the version ids are the ones the resolver writes -------------

EXAMPLE_A = ROOT / "tests" / "fixtures" / "obligations" / "versions" / "example_a.yaml"


def _flat_tree(*, dated: bool, from_: str = "2027-07-01") -> Tree:
    """Worked example A as the resolver flattens it: the original alone, or with the
    amendment that lengthens its window dated `from_`."""
    doc = yaml.safe_load(EXAMPLE_A.read_text())
    if dated:
        doc["obligations"][1]["in_force"]["from"] = from_
    else:
        del doc["obligations"][1]
    return Tree(resolve.flatten_docs([("example_a.yaml", doc)]), frozenset({"AU"}))


def test_a_newly_dated_version_from_after_the_tag_is_an_amendment_and_the_original_is_not_a_correction() -> None:
    changes = classify(_flat_tree(dated=False), _flat_tree(dated=True), date(2026, 12, 10))
    # The original gains a derived `until` and `by`: not a changed field of the original.
    assert {(c.kind, c.commences) for c in changes} == {("amendment", date(2027, 7, 1))}
    assert release_json(changes, "## v30, 2026-12-10: amendment\n", "v30")["amendments"] == [
        {"key": "payment.adjudication_application.au-vic", "from": "2027-07-01"}
    ]


def test_a_newly_dated_version_from_on_or_before_the_tag_is_a_correction() -> None:
    for tagged in (date(2027, 7, 1), date(2027, 7, 2)):
        changes = classify(_flat_tree(dated=False), _flat_tree(dated=True), tagged)
        assert computed_kinds(changes) == {"correction"}, tagged


def test_changing_a_dated_versions_window_is_a_correction_and_its_until_alone_is_not() -> None:
    old, new = _flat_tree(dated=True), _flat_tree(dated=True)
    new.instruments[0]["obligations"][1]["window"] = {"value": 20, "unit": "business_days"}
    changes = classify(old, new, date(2026, 12, 10))
    assert [(c.kind, c.key) for c in changes] == [("correction", "payment.adjudication_application.au-vic")]


def test_moving_the_start_of_a_pending_version_is_a_new_pending_version_and_a_removed_one() -> None:
    changes = classify(_flat_tree(dated=True), _flat_tree(dated=True, from_="2027-09-01"), date(2026, 12, 10))
    assert {c.kind for c in changes} == {"amendment", "correction"}
