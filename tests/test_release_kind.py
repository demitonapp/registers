"""SM052 D5: a release's kinds are computed from the diff against the previous tag,
and a tag whose CHANGELOG section does not declare them is refused.

    python -m pytest tests/test_release_kind.py -q

The first three tests read real tags, so the checkout needs them (CI checks out
with fetch-depth 0). The rest use two-row trees, and the last group flattens fixture
instruments with `resolve.py`, so a version is named by the `in_force.from` the resolver
really writes (no real tag carries a dated row yet).
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import resolve  # noqa: E402
from release_kind import (  # noqa: E402
    Tree,
    brisbane_date,
    business_days_between,
    classify,
    computed_kinds,
    heading_date,
    heading_errors,
    holiday_change,
    late_amendments,
    refusals,
    release_json,
    tree_at,
)

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
    assert release_json(changes, good, "v17") == {
        "tag": "v17",
        "kinds": ["addition", "correction"],
        "amendments": [],
        "warnings": [],
    }


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


# --- SM052 D5 review fixes: the tag date is the CHANGELOG heading's, and a warning is said once ----


def test_a_commit_in_the_evening_utc_is_the_next_day_in_brisbane() -> None:
    assert brisbane_date("2026-11-01T22:00:00Z") == date(2026, 11, 2)
    assert brisbane_date("2026-11-01T22:00:00+00:00") == date(2026, 11, 2)
    assert brisbane_date("2026-11-01T13:59:59+00:00") == date(2026, 11, 1)  # 23:59:59 in Brisbane
    assert brisbane_date("2026-11-02T00:30:00+10:00") == date(2026, 11, 2)
    with pytest.raises(ValueError):
        brisbane_date("2026-11-02T00:30:00")  # no offset, so no date: refused rather than guessed


def test_the_heading_date_must_be_the_tag_commits_date_in_brisbane() -> None:
    commit = brisbane_date("2026-11-01T22:00:00Z")  # 2 Nov in Brisbane
    changes: list = []
    assert refusals(changes, "## v17, 2026-11-02: none\n", "v17", TAG_DATE, commit) == []
    errors = refusals(changes, "## v17, 2026-11-01: none\n", "v17", TAG_DATE, commit)  # the UTC date
    assert any("2026-11-01" in e and "2026-11-02" in e and "Australia/Brisbane" in e for e in errors), errors
    assert heading_date("## v16, 2026-10-12: x\n## v17, 2026-11-02: y\n", "v17") == date(2026, 11, 2)
    assert heading_date("## v16, 2026-10-12: x\n", "v17") is None


def test_a_late_amendment_is_warned_once_not_once_per_row() -> None:
    changes = classify(_flat_tree(dated=False), _flat_tree(dated=True, from_="2026-12-12"), date(2026, 12, 10))
    assert [c.kind for c in changes].count("amendment") == 2  # the new version, and the original's derived until
    key = "payment.adjudication_application.au-vic"
    assert late_amendments(changes, date(2026, 12, 10)) == [
        f"{key} commences 2026-12-12, fewer than 20 business days after 2026-12-10"
    ]
    assert late_amendments(changes, date(2026, 10, 1)) == []  # more than 20 business days of notice
    assert release_json(changes, "## v30, 2026-12-10: amendment\n", "v30", late_amendments(changes, date(2026, 12, 10)))[
        "warnings"
    ] == [f"{key} commences 2026-12-12, fewer than 20 business days after 2026-12-10"]


def _release_repo(tmp_path: Path, *, heading: str, committed: str, amends_from: str) -> Path:
    """A throwaway repository holding this one's scripts and vocab, tagged v1 (the original
    of worked example A) and v2 (its amendment dated `amends_from`), v2 committed at the
    ISO time `committed` and its CHANGELOG headed `heading`."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    for name in ("resolve.py", "release_kind.py"):
        shutil.copy(ROOT / "scripts" / name, repo / "scripts" / name)
    shutil.copytree(ROOT / "vocab", repo / "vocab")
    (repo / "obligations" / "AU-VIC").mkdir(parents=True)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }

    def git(*args: str, when: str | None = None) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env={**env, **({"GIT_COMMITTER_DATE": when, "GIT_AUTHOR_DATE": when} if when else {})})

    doc = yaml.safe_load(EXAMPLE_A.read_text())
    amended = yaml.safe_load(EXAMPLE_A.read_text())
    amended["obligations"][1]["in_force"]["from"] = amends_from
    del doc["obligations"][1]
    target = repo / "obligations" / "AU-VIC" / "fixture.yaml"
    git("init", "-q")
    target.write_text(yaml.safe_dump(doc, sort_keys=False))
    (repo / "CHANGELOG.md").write_text("# Changelog\n")
    git("add", "-A")
    git("commit", "-q", "-m", "v1", when="2020-01-01T00:00:00+00:00")
    git("tag", "v1")
    target.write_text(yaml.safe_dump(amended, sort_keys=False))
    (repo / "CHANGELOG.md").write_text(f"# Changelog\n\n## v2, {heading}: amendment\n")
    git("add", "-A")
    git("commit", "-q", "-m", "v2", when=committed)
    git("tag", "v2")
    return repo


def _cut(repo: Path, *extra: str, github: bool = False) -> subprocess.CompletedProcess:
    commit = subprocess.run(["git", "log", "-1", "--format=%cI", "v2"], cwd=repo, capture_output=True, text=True, check=True).stdout.strip()
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
    if github:
        env["GITHUB_ACTIONS"] = "true"
    return subprocess.run(
        [sys.executable, "scripts/release_kind.py", "--base", "v1", "--tag", "v2", "--commit-date", commit, "--out", "RELEASE.json", *extra],
        cwd=repo, capture_output=True, text=True, env=env,
    )


def test_the_tag_date_is_the_changelog_heading_and_a_late_amendment_is_in_release_json(tmp_path: Path) -> None:
    # 2030-01-07 is a Monday; the amendment commences 10 weekdays later. Against today's date
    # (the old default) it would be years away and nothing would warn.
    repo = _release_repo(tmp_path, heading="2030-01-07", committed="2030-01-07T09:00:00+10:00", amends_from="2030-01-21")
    done = _cut(repo)
    assert done.returncode == 0, done.stdout + done.stderr
    key = "payment.adjudication_application.au-vic"
    text = f"{key} commences 2030-01-21, fewer than 20 business days after 2030-01-07"
    assert done.stdout.count(text) == 1, done.stdout  # once, not once per row
    release = json.loads((repo / "RELEASE.json").read_text())
    assert release == {
        "tag": "v2",
        "kinds": ["amendment"],
        "amendments": [{"key": key, "from": "2030-01-21"}],
        "warnings": [text],
    }
    annotated = _cut(repo, github=True)
    assert annotated.stdout.count(f"::warning title=Late amendment::{text}") == 1, annotated.stdout


def test_no_warning_and_an_empty_list_when_the_amendment_has_notice(tmp_path: Path) -> None:
    repo = _release_repo(tmp_path, heading="2030-01-07", committed="2030-01-07T09:00:00+10:00", amends_from="2030-03-01")
    done = _cut(repo)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "warning" not in done.stdout
    assert json.loads((repo / "RELEASE.json").read_text())["warnings"] == []


def test_a_heading_dated_by_the_utc_clock_is_refused_at_the_utc_brisbane_boundary(tmp_path: Path) -> None:
    # 22:00 UTC on 1 Nov is 08:00 on 2 Nov in Brisbane. A heading of 1 Nov is the runner's date.
    wrong = _release_repo(tmp_path / "a", heading="2026-11-01", committed="2026-11-01T22:00:00+00:00", amends_from="2027-07-01")
    done = _cut(wrong)
    assert done.returncode == 1, done.stdout
    assert "2026-11-01" in done.stdout and "2026-11-02" in done.stdout and "Australia/Brisbane" in done.stdout
    assert not (wrong / "RELEASE.json").exists()

    right = _release_repo(tmp_path / "b", heading="2026-11-02", committed="2026-11-01T22:00:00+00:00", amends_from="2027-07-01")
    done = _cut(right)
    assert done.returncode == 0, done.stdout
    assert json.loads((right / "RELEASE.json").read_text())["warnings"] == []


# --- SM052 D5 re-review: holiday calendars and a withdrawn jurisdiction are release kinds -------

QLD = ROOT / "holidays" / "AU-QLD.yaml"


def _holiday_repo(tmp_path: Path, edit, *, changelog: str = "") -> Path:
    """A throwaway repository holding this one's scripts, vocab and the real AU-QLD calendar,
    tagged v1, then `edit(repo)` applied and committed as v2. No obligations: the kinds this
    exercises are the ones computed from holidays/ and vocab/."""
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    for name in ("resolve.py", "release_kind.py"):
        shutil.copy(ROOT / "scripts" / name, repo / "scripts" / name)
    shutil.copytree(ROOT / "vocab", repo / "vocab")
    (repo / "holidays").mkdir()
    shutil.copy(QLD, repo / "holidays" / "AU-QLD.yaml")
    shutil.copy(ROOT / "holidays" / "calendar.schema.json", repo / "holidays" / "calendar.schema.json")
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    }

    def git(*args: str) -> None:
        subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, env=env)

    git("init", "-q")
    (repo / "CHANGELOG.md").write_text("# Changelog\n")
    git("add", "-A")
    git("commit", "-q", "-m", "v1")
    git("tag", "v1")
    edit(repo)
    (repo / "CHANGELOG.md").write_text(changelog or "# Changelog\n")
    git("add", "-A")
    git("commit", "-q", "-m", "v2")
    git("tag", "v2")
    return repo


def _kinds(repo: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/release_kind.py", "--base", "v1", "--on", "2026-11-02", *extra],
        cwd=repo, capture_output=True, text=True,
    )


def _edit_qld(old: str, new: str):
    def edit(repo: Path) -> None:
        path = repo / "holidays" / "AU-QLD.yaml"
        text = path.read_text()
        assert text.count(old) == 1, old
        path.write_text(text.replace(old, new))
    return edit


def _new_year(repo: Path) -> None:
    path = repo / "holidays" / "AU-QLD.yaml"
    text = path.read_text().replace("years: [2025, 2026, 2027]", "years: [2025, 2026, 2027, 2028]")
    text = text.replace("not_included:\n", '  - date: "2028-01-01"\n    name: "New Year\'s Day"\nnot_included:\n', 1)
    path.write_text(text)


def _unsupport_nz(repo: Path) -> None:
    path = repo / "vocab" / "jurisdictions.json"
    vocab = json.loads(path.read_text())
    assert vocab["NZ"]["supported"] is True
    vocab["NZ"]["supported"] = False
    path.write_text(json.dumps(vocab, indent=2) + "\n")


def test_an_unchanged_holiday_calendar_computes_none(tmp_path: Path) -> None:
    done = _kinds(_holiday_repo(tmp_path, lambda repo: (repo / "README.md").write_text("x\n")))
    assert done.returncode == 0, done.stdout + done.stderr
    assert "kinds: none" in done.stdout, done.stdout


def test_a_reflowed_holiday_calendar_is_no_change(tmp_path: Path) -> None:
    done = _kinds(_holiday_repo(tmp_path, lambda repo: (repo / "holidays" / "AU-QLD.yaml").write_text(
        (repo / "holidays" / "AU-QLD.yaml").read_text().replace('name: "Labour Day"', "name: 'Labour Day'")
    )))
    assert "kinds: none" in done.stdout, done.stdout


def test_a_changed_holiday_date_is_a_correction_that_names_the_file(tmp_path: Path) -> None:
    done = _kinds(_holiday_repo(tmp_path, _edit_qld('date: "2026-05-04"', 'date: "2026-05-11"')))
    assert "kinds: correction" in done.stdout, done.stdout
    assert "holidays/AU-QLD.yaml" in done.stdout, done.stdout


def test_a_removed_holiday_date_is_a_correction(tmp_path: Path) -> None:
    done = _kinds(_holiday_repo(tmp_path, _edit_qld('  - date: "2026-12-28"\n    name: "Additional public holiday for Boxing Day"\n', "")))
    assert "kinds: correction" in done.stdout, done.stdout


def test_only_a_new_year_is_an_addition(tmp_path: Path) -> None:
    done = _kinds(_holiday_repo(tmp_path, _new_year))
    assert "kinds: addition" in done.stdout, done.stdout
    assert "holidays/AU-QLD.yaml" in done.stdout, done.stdout


def test_a_new_year_that_also_changes_an_old_date_is_a_correction_too() -> None:
    old = yaml.safe_load(QLD.read_text())
    new = yaml.safe_load(QLD.read_text())
    new["years"].append(2028)
    new["holidays"].append({"date": "2028-01-01", "name": "New Year's Day"})
    assert holiday_change("holidays/AU-QLD.yaml", old, new).kind == "addition"
    new["holidays"][0]["date"] = "2025-01-02"
    assert holiday_change("holidays/AU-QLD.yaml", old, new).kind == "correction"


def test_a_date_added_to_a_year_the_file_listed_as_complete_is_a_correction() -> None:
    old = yaml.safe_load(QLD.read_text())
    new = yaml.safe_load(QLD.read_text())
    new["holidays"].append({"date": "2026-08-12", "name": "A holiday the calendar missed"})
    change = holiday_change("holidays/AU-QLD.yaml", old, new)
    assert change.kind == "correction" and "holidays/AU-QLD.yaml" in change.reason


def test_a_changed_field_a_removed_year_and_a_removed_file_are_corrections_and_a_new_file_an_addition() -> None:
    old = yaml.safe_load(QLD.read_text())
    reworded = {**old, "weekend_rule": "changed"}
    assert holiday_change("holidays/AU-QLD.yaml", old, reworded).kind == "correction"
    fewer = {**old, "years": old["years"][:-1]}
    assert holiday_change("holidays/AU-QLD.yaml", old, fewer).kind == "correction"
    assert holiday_change("holidays/AU-QLD.yaml", old, None).kind == "correction"
    assert holiday_change("holidays/AU-QLD.yaml", None, old).kind == "addition"
    assert holiday_change("holidays/AU-QLD.yaml", old, old) is None


def test_a_holiday_correction_must_be_declared_by_the_tag(tmp_path: Path) -> None:
    edit = _edit_qld('date: "2026-05-04"', 'date: "2026-05-11"')
    bare = _holiday_repo(tmp_path / "a", edit, changelog="# Changelog\n\n## v2, 2026-11-02: addition\n")
    done = _kinds(bare, "--tag", "v2", "--commit-date", "2026-11-02T09:00:00+10:00")
    assert done.returncode == 1, done.stdout
    assert "correction" in done.stdout and "holidays/AU-QLD.yaml" in done.stdout, done.stdout
    ok = _holiday_repo(tmp_path / "b", edit, changelog="# Changelog\n\n## v2, 2026-11-02: correction\n")
    done = _kinds(ok, "--tag", "v2", "--commit-date", "2026-11-02T09:00:00+10:00", "--out", "RELEASE.json")
    assert done.returncode == 0, done.stdout + done.stderr
    assert json.loads((ok / "RELEASE.json").read_text()) == {"tag": "v2", "kinds": ["correction"], "amendments": [], "warnings": []}


def test_a_jurisdiction_switched_to_unsupported_is_a_correction(tmp_path: Path) -> None:
    done = _kinds(_holiday_repo(tmp_path, _unsupport_nz))
    assert "kinds: correction" in done.stdout, done.stdout
    assert "NZ" in done.stdout and "unsupported" in done.stdout, done.stdout
    changes = classify(Tree([], frozenset({"AU", "NZ"})), Tree([], frozenset({"AU"})), TAG_DATE)
    assert [(c.kind, c.key) for c in changes] == [("correction", "NZ")]
    assert "NZ" in changes[0].reason
    # and a jurisdiction switched on is still an addition
    assert [(c.kind, c.key) for c in classify(Tree([], frozenset({"AU"})), Tree([], frozenset({"AU", "NZ"})), TAG_DATE)] == [("addition", "NZ")]


def test_a_tag_from_before_holidays_existed_still_reads(tags) -> None:
    assert tags["v13"].holidays == {} or all(k.startswith("holidays/") for k in tags["v13"].holidays)


def test_the_real_tree_has_no_holiday_change_against_itself() -> None:
    here = tree_at("HEAD")
    assert "holidays/AU-QLD.yaml" in here.holidays
    assert [c for c in classify(here, here, TAG_DATE)] == []


# --- the heading of the tag's section -------------------------------------------------------


def test_two_headings_for_one_tag_are_refused() -> None:
    changelog = "## v17, 2026-11-02: correction\n\n## v17, 2026-11-09: addition\n"
    errors = refusals([], changelog, "v17", TAG_DATE)
    assert len(errors) == 1 and "2 `## v17` headings" in errors[0] and "2026-11-02" in errors[0] and "2026-11-09" in errors[0], errors
    assert heading_errors("## v17, 2026-11-02: none\n## v18, 2026-11-09: none\n", "v17") == []  # two tags, one heading each


def test_an_impossible_heading_date_is_a_refusal_not_a_traceback() -> None:
    errors = refusals([], "## v17, 2026-13-45: none\n", "v17", TAG_DATE)
    assert len(errors) == 1 and "2026-13-45" in errors[0] and "not a calendar date" in errors[0], errors
    with pytest.raises(ValueError):
        heading_date("## v17, 2026-13-45: none\n", "v17")  # callers go through heading_errors first


def test_the_command_line_refuses_both_cleanly(tmp_path: Path) -> None:
    for n, (changelog, expect) in enumerate((
        ("# Changelog\n\n## v2, 2026-13-45: none\n", "2026-13-45"),
        ("# Changelog\n\n## v2, 2026-11-02: none\n\n## v2, 2026-11-03: none\n", "2 `## v2` headings"),
    )):
        repo = _holiday_repo(tmp_path / str(n), lambda repo: (repo / "README.md").write_text("x\n"), changelog=changelog)
        done = _kinds(repo, "--tag", "v2", "--commit-date", "2026-11-02T09:00:00+10:00")
        assert done.returncode == 1, done.stdout
        assert "Traceback" not in done.stderr and expect in done.stdout, done.stdout + done.stderr
