"""SM031 M4 Acceptance: the resolver flattens a base and its overrides, and the
checks that need more than one document refuse a tree that cannot flatten.

    python -m pytest tests/test_resolve.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import resolve  # noqa: E402
from validate import validate_instrument_doc  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "obligations"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _tree(*names: str) -> list[tuple[str, dict]]:
    return [(name, _load(FIXTURES / name)) for name in names]


def test_cycle_is_refused() -> None:
    errors = resolve.tree_errors(_tree("tree/cycle/cyc_a.yaml", "tree/cycle/cyc_b.yaml"))
    assert any("cycle" in e for e in errors), errors


def test_orphan_override_is_refused() -> None:
    errors = resolve.tree_errors(_tree("tree/orphan/base.yaml", "tree/orphan/concrete.yaml"))
    assert any("not an obligation of base" in e for e in errors), errors


def test_silent_drop_is_refused() -> None:
    errors = resolve.tree_errors(_tree("tree/silent_drop/base.yaml", "tree/silent_drop/concrete.yaml"))
    assert any("silently drop" in e for e in errors), errors


def test_forbidden_field_override_is_refused() -> None:
    doc = _load(FIXTURES / "invalid" / "forbidden_field_override.yaml")
    errors = validate_instrument_doc(doc, "invalid/forbidden_field_override.yaml")
    assert any("duty" in e for e in errors), errors


def test_removed_row_is_accepted_and_emits_nothing() -> None:
    """Decision 10: the explicit way to drop a base obligation. The row carries
    no key and produces no flattened obligation."""
    base = _load(FIXTURES / "tree/silent_drop/base.yaml")
    concrete = _load(FIXTURES / "tree/silent_drop/concrete.yaml")
    concrete = dict(concrete)
    concrete["obligations"] = list(concrete["obligations"]) + [{"overrides": "drop.two", "removed": True}]
    assert resolve.tree_errors([("base.yaml", base), ("concrete.yaml", concrete)]) == []

    by_id = {base["id"]: (base, "base.yaml"), concrete["id"]: (concrete, "concrete.yaml")}
    flat = resolve.resolve_instrument(concrete, by_id)
    assert [o["key"] for o in flat["obligations"]] == ["drop.one.au-qld"]


def test_concrete_flattens_to_the_base_duty_with_its_own_citation() -> None:
    """The point of the mechanism: the duty is written once in the base, and the
    state's row is only what differs - its key, clause, citation and grade."""
    base = _load(FIXTURES / "valid" / "abstract_base.yaml")
    concrete = _load(FIXTURES / "valid" / "extending_concrete.yaml")
    by_id = {base["id"]: (base, "base.yaml"), concrete["id"]: (concrete, "concrete.yaml")}

    flat = resolve.resolve_instrument(concrete, by_id)
    assert flat["id"] == "fixture_state_act"
    assert flat["source"] == "law"                    # inherited from the base
    assert flat["instrument_type"] == "act"           # inherited from the base
    assert flat["jurisdictions"] == ["AU-QLD"]        # stated by the concrete
    assert "extends" not in flat and "abstract" not in flat
    assert [o["key"] for o in flat["obligations"]] == ["fixture.notice.au-qld"]
    row = flat["obligations"][0]
    assert row["duty"] == base["obligations"][0]["duty"]
    assert row["disease"] == base["obligations"][0]["disease"]
    assert row["grade"] == "primary_read"
    assert row["citation"]["url"].endswith("fixture-state-act-2026")


def test_a_concrete_that_leaves_the_grade_to_the_base_is_refused() -> None:
    """M3's bases leave `grade` to the concrete that first reads the state's own
    text, so a concrete that supplies neither must not flatten into a row that
    claims a grade it never had."""
    base = _load(FIXTURES / "valid" / "abstract_base.yaml")
    concrete = _load(FIXTURES / "valid" / "extending_concrete.yaml")
    concrete = dict(concrete)
    concrete["obligations"] = [{"overrides": "fixture.notice", "key": "fixture.notice.au-qld"}]
    errors = resolve.tree_errors([("base.yaml", base), ("concrete.yaml", concrete)])
    assert any("no grade" in e for e in errors), errors


# --- SM031 M2: the model-law bases and the WHS rework ----------------------


def test_whs_concrete_resolves_to_model_base() -> None:
    """Seven WHS/OHS acts carried the same three notifiable-incident duties word
    for word. After M2 they resolve through one base, and each state's row keeps
    its own key and its own citation."""
    concretes, by_id = resolve.load_tree()
    acts = {d["id"]: d for d in concretes if d.get("extends") == "model_whs_act_2011"}
    assert sorted(acts) == [
        "whs_act_2011_act",
        "whs_act_2011_nsw",
        "whs_act_2011_qld",
        "whs_act_2012_sa",
        "whs_act_2012_tas",
        "whs_act_2020_wa",
        "whs_nul_act_2011_nt",
    ]
    base = by_id["model_whs_act_2011"][0]
    assert [o["key"] for o in base["obligations"]] == [
        "whs.incident_notice",
        "whs.incident_written_notice",
        "whs.incident_record",
    ]
    for iid, doc in acts.items():
        flat = resolve.resolve_instrument(doc, by_id)
        assert [o["key"] for o in flat["obligations"]] == [o["key"] for o in doc["obligations"]], iid
        assert [o["duty"] for o in flat["obligations"]] == [o["duty"] for o in base["obligations"]], iid
        assert flat["id"] == iid
    qld = resolve.resolve_instrument(acts["whs_act_2011_qld"], by_id)
    assert qld["obligations"][0]["citation"]["url"].startswith("https://www.legislation.qld.gov.au")
    assert qld["publisher"] == "Queensland Parliament"

    regs = {d["id"]: d for d in concretes if d.get("extends") == "model_whs_regulations_2011"}
    assert sorted(regs) == [
        "whs_general_regulations_2022_wa",
        "whs_nul_regulations_2011_nt",
        "whs_regulation_2011_act",
        "whs_regulation_2011_qld",
        "whs_regulation_2025_nsw",
        "whs_regulations_2012_sa",
        "whs_regulations_2022_tas",
    ]
    nsw = resolve.resolve_instrument(regs["whs_regulation_2025_nsw"], by_id)
    assert nsw["obligations"][0]["clause"] == "s 304(2), (6)"  # NSW calls it a section
    qld_reg = resolve.resolve_instrument(regs["whs_regulation_2011_qld"], by_id)
    assert qld_reg["obligations"][0]["clause"] == "r 304(2), (6)"


def test_flattening_emits_exactly_the_overrides_each_concrete_carries() -> None:
    """Deliberately branch-independent. A hardcoded total fails for a reason
    unrelated to this package the moment another obligation PR merges, so what is
    asserted is the arithmetic of flattening itself: a standalone concrete emits
    one row per obligation it states, and an extending concrete emits one row per
    override it carries, less the rows it marks `removed`. A silent drop, a double
    emission, or an override that adopts nothing breaks the equality. M6's rows
    are the only ones this package adds, and they sit on top of the pre-M6 set."""
    concretes, by_id = resolve.load_tree()
    for doc in concretes:
        flat = resolve.resolve_instrument(doc, by_id)
        if "extends" not in doc:
            expected = len(doc["obligations"])
        else:
            base = by_id[doc["extends"]][0]
            if base.get("model_type") == "shared_shape":
                expected = len([o for o in doc["obligations"] if not o.get("removed")])
            else:
                removed = len([o for o in doc["obligations"] if o.get("removed")])
                expected = len(base["obligations"]) - removed
        assert len(flat["obligations"]) == expected, doc["id"]

    assert resolve.count() > 196, "M6 adds rows; the pre-M6 concrete set was 196"


# --- SM031 M6: the first concrete buckets ----------------------------------


def test_queensland_approvals_resolve_to_their_bases() -> None:
    """The first approvals concrete: the Environmental Protection Act 1994 (Qld)
    states the compliance offence and the regulator notification, so those two
    duties of the shared shape are adopted and the third is not."""
    concretes, by_id = resolve.load_tree()
    doc = next(d for d in concretes if d["id"] == "environmental_authority_ep_act_1994_qld")
    flat = resolve.resolve_instrument(doc, by_id)

    assert flat["source"] == "approvals"
    assert [o["key"] for o in flat["obligations"]] == [
        "approvals.environmental_authority_conditions.au-qld",
        "approvals.environmental_authority_incident_notice.au-qld",
    ]
    assert flat["obligations"][0]["citation"]["clause"] == "s 430"
    assert flat["obligations"][1]["window"] == {"value": 24, "unit": "hours"}
    base = by_id["model_environmental_authority"][0]
    assert flat["obligations"][0]["duty"] == base["obligations"][0]["duty"]
    assert flat["obligations"][0]["grade"] == "primary_read"
    # The records duty (base obligation 3) is not adopted, so nothing emits it.
    assert "approvals.environmental_authority_records.au-qld" not in [o["key"] for o in flat["obligations"]]


def test_the_buckets_m6_could_author_contribute_obligations() -> None:
    """M6's acceptance. `approvals` and `workforce` were empty and now contribute;
    `own_commitments` keeps its three Demiton defaults. Two buckets stay empty on
    purpose and are named in the CHANGELOG rather than filled with a shape that
    cites nothing: `counterparties`, because an insurer's notification clause
    lives in the policy a given org holds and no national instrument carries it,
    and the NSW half of `approvals`, because legislation.nsw.gov.au is
    unreachable from the build environment."""
    concretes, by_id = resolve.load_tree()
    counts: dict[str, int] = {}
    for doc in concretes:
        flat = resolve.resolve_instrument(doc, by_id)
        counts[flat["source"]] = counts.get(flat["source"], 0) + len(flat["obligations"])

    assert counts["approvals"] >= 4
    assert counts["workforce"] >= 1
    assert counts["own_commitments"] >= 5
    assert counts.get("counterparties", 0) == 0


def test_new_south_wales_approvals_resolve_and_clear_a_window() -> None:
    """The NSW half of M6. `legislation.nsw.gov.au` answers HTTP 403 from the
    build environment, so the clauses were read from the Internet Archive's
    copies of the government's own whole-Act page and XML export. Two rows clear
    a window the base states, because both duties run "immediately" or "within a
    reasonable time" rather than to a fixed period."""
    concretes, by_id = resolve.load_tree()
    nsw = {
        d["id"]: d
        for d in concretes
        if d.get("jurisdictions") == ["AU-NSW"]
        and str(d.get("extends", "")).startswith("model_")
        and by_id[d["extends"]][0]["source"] == "approvals"
    }
    assert sorted(nsw) == [
        "aboriginal_heritage_npwa_1974_nsw",
        "environmental_protection_licence_poeo_act_1997_nsw",
        "vegetation_clearing_lls_act_2013_nsw",
        "waterway_barrier_fisheries_management_act_1994_nsw",
    ]

    base = by_id["model_aboriginal_heritage"][0]
    base_row = next(o for o in base["obligations"] if o["key"].endswith("aboriginal_heritage_find"))
    assert base_row["window"] == {"value": 24, "unit": "hours"}

    flat = resolve.resolve_instrument(nsw["aboriginal_heritage_npwa_1974_nsw"], by_id)
    row = next(o for o in flat["obligations"] if o["key"].endswith("aboriginal_heritage_find.au-nsw"))
    assert "window" not in row, "the base's 24-hour window is cleared, not inherited"
    assert row["clause"] == "s 89A"
    assert row["duty"] == base_row["duty"]

    poeo = resolve.resolve_instrument(nsw["environmental_protection_licence_poeo_act_1997_nsw"], by_id)
    notice = next(o for o in poeo["obligations"] if o["key"].endswith("incident_notice.au-nsw"))
    assert notice["clause"] == "s 148(2), (3)"
    assert "window" not in notice


def test_a_row_without_an_approval_class_is_refused() -> None:
    # SM037: every resolved row names the kind of sign-off its evidence needs.
    tree = _tree("tree/silent_drop/base.yaml", "tree/silent_drop/concrete.yaml")
    _rel, base = tree[0]
    del base["obligations"][0]["approval_class"]
    errors = resolve.tree_errors(tree)
    assert any("has no approval_class" in e for e in errors), errors


def test_a_row_without_a_duty_shape_is_refused() -> None:
    # Every resolved row names the duty it states, so it reads beside the same
    # duty from another instrument. An override inherits it, so a base without
    # one leaves its resolved rows without one.
    tree = _tree("tree/silent_drop/base.yaml", "tree/silent_drop/concrete.yaml")
    _rel, base = tree[0]
    del base["obligations"][0]["duty_shape"]
    errors = resolve.tree_errors(tree)
    assert any("has no duty_shape" in e for e in errors), errors


def test_a_duty_shape_outside_the_vocabulary_is_refused() -> None:
    tree = _tree("tree/silent_drop/base.yaml", "tree/silent_drop/concrete.yaml")
    _rel, base = tree[0]
    base["obligations"][0]["duty_shape"] = "latent_conditions.made_up"
    errors = resolve.tree_errors(tree)
    assert any("'latent_conditions.made_up' is not in vocab/duty_shapes.json" in e for e in errors), errors


# --- SM052 D1: dated versions of one duty -----------------------------------

VERSIONS = FIXTURES / "versions"
AMENDED = "payment.adjudication_application.au-vic"


def _flatten(name: str) -> list[dict]:
    return resolve.flatten_docs([(name, _load(VERSIONS / name))])


def _assert_contiguous(instruments: list[dict]) -> int:
    """Every key's versions, oldest first: each starts the day after the one before ends,
    and only the first may have no `from`. Returns how many keys have several versions."""
    from datetime import date, timedelta

    keys = 0
    for inst in instruments:
        groups: dict[str, list[dict]] = {}
        for row in inst["obligations"]:
            groups.setdefault(row["key"], []).append(row)
        for key, rows in groups.items():
            if len(rows) < 2:
                continue
            keys += 1
            rows.sort(key=lambda r: (r.get("in_force") or {}).get("from") or "")
            assert "from" not in rows[0].get("in_force", {}), key
            for before, after in zip(rows, rows[1:]):
                until = date.fromisoformat(before["in_force"]["until"])
                assert date.fromisoformat(after["in_force"]["from"]) == until + timedelta(days=1), key
    return keys


def test_versions_of_one_key_are_contiguous_after_resolve() -> None:
    """Worked example A: one file holds the old and the new rule of a duty. It flattens to
    two rows under one key, and the original is given the day before the amendment as its
    `until`, decided by the same date the amendment is."""
    flat = _flatten("example_a.yaml")
    assert len(flat) == 1
    rows = flat[0]["obligations"]
    assert [r["key"] for r in rows] == [AMENDED, AMENDED]
    original, amended = rows
    assert original["in_force"] == {"until": "2027-06-30", "by": "event_date"}
    assert original["window"] == {"value": 10, "unit": "business_days"}
    assert amended["in_force"]["from"] == "2027-07-01"
    assert amended["in_force"]["by"] == "event_date"
    assert "until" not in amended["in_force"]
    assert amended["window"] == {"value": 15, "unit": "business_days"}
    assert _assert_contiguous(flat) == 1
    # And the real library, which has none yet, flattens through the same code.
    _assert_contiguous(resolve.flatten())


def test_three_versions_chain_and_a_repeal_stays_on_the_last() -> None:
    doc = _load(VERSIONS / "repeal.yaml")
    middle = dict(doc["obligations"][1])
    middle["in_force"] = {"from": "2027-07-01", "by": "event_date"}
    last = dict(doc["obligations"][1])
    last["in_force"] = {"from": "2028-01-01", "until": "2029-12-31", "by": "event_date"}
    doc["obligations"] = [doc["obligations"][0], middle, last]
    assert resolve.tree_errors([("f", doc)]) == []
    rows = resolve.flatten_docs([("f", doc)])[0]["obligations"]
    assert [r["in_force"].get("from") for r in rows] == [None, "2027-07-01", "2028-01-01"]
    assert [r["in_force"].get("until") for r in rows] == ["2027-06-30", "2027-12-31", "2029-12-31"]
    assert _assert_contiguous([{"obligations": rows}]) == 1


def test_rows_keep_their_authored_order_whatever_the_order_of_the_versions() -> None:
    doc = _load(VERSIONS / "example_a.yaml")
    doc["obligations"].reverse()  # the new rule written first
    rows = resolve.flatten_docs([("f", doc)])[0]["obligations"]
    assert [r["window"]["value"] for r in rows] == [15, 10]
    assert rows[1]["in_force"]["until"] == "2027-06-30"


def test_a_derived_until_names_the_next_versions_date_when_it_differs() -> None:
    doc = _load(VERSIONS / "example_a.yaml")
    doc["obligations"][0]["in_force"] = {"from": "2020-01-01", "by": "contract_date"}
    rows = resolve.flatten_docs([("f", doc)])[0]["obligations"]
    assert rows[0]["in_force"] == {"from": "2020-01-01", "by": "contract_date", "until": "2027-06-30", "until_by": "event_date"}


def test_an_instrument_level_in_force_is_copied_onto_every_row_that_states_none() -> None:
    """Worked example B: an Act dated once, on the instrument."""
    doc = _load(VERSIONS / "instrument_level.yaml")
    inst = resolve.flatten_docs([("f", doc)])[0]
    block = {"from": "2022-08-01", "by": "contract_date", "transitional": "s 9(1)"}
    head, principal, own = inst["obligations"]
    assert head["in_force"] == block and principal["in_force"] == block
    assert head["in_force"] is not principal["in_force"], "each row gets its own copy"
    assert own["in_force"] == {"from": "2023-01-01", "by": "contract_date"}, "a row's own block is kept, not merged"
    assert inst["in_force"] == block


def test_an_extending_concrete_may_carry_a_second_override_of_one_base_key_as_a_version() -> None:
    base = _load(FIXTURES / "valid" / "abstract_base.yaml")
    concrete = _load(FIXTURES / "valid" / "extending_concrete.yaml")
    later = dict(concrete["obligations"][0], clause="s 1A", in_force={"from": "2028-01-01", "by": "event_date"})
    concrete["obligations"] = [dict(concrete["obligations"][0]), later]
    docs = [("base.yaml", base), ("concrete.yaml", concrete)]
    assert resolve.tree_errors(docs) == []
    rows = resolve.flatten_docs(docs)[0]["obligations"]
    assert [r["key"] for r in rows] == ["fixture.notice.au-qld"] * 2
    assert rows[0]["in_force"] == {"until": "2027-12-31", "by": "event_date"}
    assert rows[1]["clause"] == "s 1A"
    # The duty is the base's in both, and a version cannot change it: overrides refuse the field.
    assert rows[0]["duty"] == rows[1]["duty"] == base["obligations"][0]["duty"]


def test_dates_come_out_as_text_whether_the_author_quoted_them_or_not() -> None:
    import json

    doc = _load(VERSIONS / "example_a.yaml")  # unquoted in the file: yaml loads them as dates
    assert hasattr(doc["obligations"][1]["in_force"]["from"], "isoformat")
    flat = resolve.flatten_docs([("f", doc)])
    json.dumps(flat)  # would raise on a date object
    assert flat[0]["obligations"][1]["in_force"]["from"] == "2027-07-01"
