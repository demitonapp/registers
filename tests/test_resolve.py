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
        "whs_regulation_2011_act",
        "whs_regulation_2011_qld",
        "whs_regulation_2025_nsw",
        "whs_regulations_2012_sa",
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
