"""SM030 O1 Acceptance: the obligation-library validator refuses what it must
refuse and passes what it must pass.

    python -m pytest tests/test_validate_obligations.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate import validate_instrument_doc  # noqa: E402
import resolve  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures" / "obligations"


def _load(path: Path) -> object:
    return yaml.safe_load(path.read_text())


def test_valid_fixture_passes() -> None:
    doc = _load(FIXTURES / "valid" / "example.yaml")
    assert validate_instrument_doc(doc, "valid/example.yaml") == []


def test_row_without_primary_citation_is_refused() -> None:
    doc = _load(FIXTURES / "invalid" / "no_citation.yaml")
    errors = validate_instrument_doc(doc, "invalid/no_citation.yaml")
    assert errors, "an obligation with no citation must be refused"
    assert any("citation" in e for e in errors)


def test_unknown_jurisdiction_is_refused() -> None:
    doc = _load(FIXTURES / "invalid" / "unknown_jurisdiction.yaml")
    errors = validate_instrument_doc(doc, "invalid/unknown_jurisdiction.yaml")
    assert errors, "an unknown jurisdiction code must be refused"
    assert any("jurisdictions.json" in e for e in errors)


def test_protection_type_outside_the_four_is_refused() -> None:
    doc = _load(FIXTURES / "invalid" / "bad_protection_type.yaml")
    errors = validate_instrument_doc(doc, "invalid/bad_protection_type.yaml")
    assert errors, "a protection_type outside the four must be refused"
    assert any("protection_type" in e for e in errors)


def test_threshold_obligation_without_its_threshold_is_refused() -> None:
    doc = _load(FIXTURES / "invalid" / "threshold_without_direction.yaml")
    errors = validate_instrument_doc(doc, "invalid/threshold_without_direction.yaml")
    assert any("must say its threshold" in e for e in errors)


def test_threshold_direction_outside_max_and_min_is_refused() -> None:
    doc = _load(FIXTURES / "invalid" / "threshold_without_direction.yaml")
    doc["obligations"][0]["threshold"] = {"direction": "lowest", "set_by": "library"}
    errors = validate_instrument_doc(doc, "fixture")
    assert any("direction" in e or "lowest" in e for e in errors)


# --- SM031 M1: the inheritance schema fields -------------------------------


def test_abstract_base_and_extending_concrete_pass() -> None:
    """The two valid shapes SM031 adds: a base in obligations/_model/ with no
    jurisdiction and no grade, and the concrete that extends it."""
    assert validate_instrument_doc(_load(FIXTURES / "valid" / "abstract_base.yaml"), "base") == []
    assert validate_instrument_doc(_load(FIXTURES / "valid" / "extending_concrete.yaml"), "concrete") == []


def test_extends_resolves_to_abstract_base() -> None:
    """`extends` resolves to an instrument id, and that instrument must be a base.
    A concrete extending a non-abstract instrument is refused by the tree check."""
    base = _load(FIXTURES / "valid" / "abstract_base.yaml")
    concrete = _load(FIXTURES / "valid" / "extending_concrete.yaml")
    assert resolve.tree_errors([("base.yaml", base), ("concrete.yaml", concrete)]) == []

    points_at_concrete = dict(concrete, extends="fixture_state_act")
    errors = resolve.tree_errors([("base.yaml", base), ("concrete.yaml", points_at_concrete)])
    assert any("not abstract" in e for e in errors), errors

    missing = _load(FIXTURES / "invalid" / "extends_missing_base.yaml")
    errors = resolve.tree_errors([("invalid/extends_missing_base.yaml", missing)])
    assert any("not the id of any instrument" in e for e in errors), errors


def test_non_abstract_requires_jurisdiction() -> None:
    """A concrete names where it applies; a base names no place."""
    errors = validate_instrument_doc(_load(FIXTURES / "invalid" / "non_abstract_empty_jurisdictions.yaml"), "concrete")
    assert any("jurisdictions" in e for e in errors), errors

    errors = validate_instrument_doc(_load(FIXTURES / "invalid" / "abstract_with_jurisdiction.yaml"), "base")
    assert any("jurisdictions" in e for e in errors), errors


def test_model_type_requires_abstract() -> None:
    """`model_type` says which tier a base is, so a concrete carrying one is
    refused, and an abstract instrument without one is refused too."""
    errors = validate_instrument_doc(_load(FIXTURES / "invalid" / "model_type_on_concrete.yaml"), "concrete")
    assert any("model_type" in e for e in errors), errors

    base = _load(FIXTURES / "valid" / "abstract_base.yaml")
    base.pop("model_type")
    errors = validate_instrument_doc(base, "base")
    assert any("model_type" in e for e in errors), errors


def test_shared_shape_bases_are_abstract() -> None:
    """SM031 M3: every base under obligations/_model/ is abstract and carries the
    model_type that says which tier it is. M3 authors the four shared-shape
    families; M2 authors the model-law pair."""
    bases = resolve.base_files()
    assert bases, "obligations/_model/ holds the bases"
    for path in bases:
        doc = _load(path)
        assert doc.get("abstract") is True, path
        assert doc.get("model_type") in ("model_law", "shared_shape"), path
        assert doc.get("jurisdictions") == [], path
        assert doc["model_type"].replace("_", "-") in path.parts, f"{path} is not filed under its model_type"


def test_unknown_trigger_is_refused() -> None:
    # Demiton SM038: a trigger must name an event type in vocab/event_types.json.
    doc = _load(FIXTURES / "valid" / "example.yaml")
    doc["obligations"][0]["trigger"] = "no_such_event"
    errors = validate_instrument_doc(doc, "example.yaml")
    assert any("is not in vocab/event_types.json" in e for e in errors), errors


def test_event_type_naming_a_missing_field_is_refused() -> None:
    from validate import validate_event_types

    errors = validate_event_types({
        "claim_lodged": {"register": "progress_claim", "date_field": "no_such_field",
                         "subject": "reference", "reference_field": "document_no"},
    })
    assert any("has no field 'no_such_field'" in e for e in errors), errors


def test_shipped_catalogue_is_valid() -> None:
    from validate import validate_event_types

    assert validate_event_types() == []


def test_requires_item_naming_a_missing_item_field_is_refused() -> None:
    from validate import validate_event_types

    errors = validate_event_types({
        "latent_condition_reported": {"register": "site_diary", "date_field": "occurred_on", "subject": "project",
                                      "requires_item": {"field": "delays", "match": {"no_such": "x"}}},
    })
    assert any("delays[] has no field 'no_such'" in e for e in errors), errors


def test_match_value_the_field_can_never_hold_is_refused() -> None:
    from validate import validate_event_types

    errors = validate_event_types({
        "notifiable_incident_recorded": {"register": "safety_incident", "date_field": "occurred_at",
                                         "subject": "reference", "reference_field": "external_id",
                                         "match": {"notifiable": "true"}},
        "latent_condition_reported": {"register": "site_diary", "date_field": "occurred_on", "subject": "project",
                                      "requires_item": {"field": "delays", "match": {"kind": "latent"}}},
    })
    assert any("notifiable is a boolean, not 'true'" in e for e in errors), errors
    assert any("delays[].kind is never 'latent'" in e for e in errors), errors


def test_lang_is_a_primary_language_subtag() -> None:
    doc = _load(FIXTURES / "valid" / "example.yaml")
    doc["lang"] = "fr"
    assert validate_instrument_doc(doc, "valid/example.yaml") == []
    doc["lang"] = "French"
    errors = validate_instrument_doc(doc, "valid/example.yaml")
    assert any("lang" in e for e in errors), "a language name, not a subtag, must be refused"


# --- SM052 D1: dated versions of one duty -----------------------------------

VERSIONS = FIXTURES / "versions"
AMENDED = "payment.adjudication_application.au-vic"


def _version_tree_errors(name: str) -> list[str]:
    return resolve.tree_errors([(name, _load(VERSIONS / name))])


def test_worked_example_a_and_the_instrument_level_example_b_pass() -> None:
    for name in ("example_a.yaml", "instrument_level.yaml", "repeal.yaml"):
        doc = _load(VERSIONS / name)
        assert validate_instrument_doc(doc, name) == [], name
        assert resolve.tree_errors([(name, doc)]) == [], name


def test_selecting_dates_are_exactly_the_two_the_engine_reads() -> None:
    assert resolve.selecting_dates() == ("contract_date", "event_date")


def test_dated_version_changing_routing_is_refused() -> None:
    """Decision 10: versions of one key share protection_type, disease, evidence.register
    and duty_shape; a change to any of them is a new key."""
    errors = _version_tree_errors("changed_protection_type.yaml")
    assert any(AMENDED in e and "protection_type" in e and "'watch'" in e and "'countdown'" in e for e in errors), errors
    errors = _version_tree_errors("changed_register.yaml")
    assert any(AMENDED in e and "evidence.register" in e for e in errors), errors


def test_overlapping_versions_are_refused_and_name_the_key() -> None:
    errors = _version_tree_errors("overlap.yaml")
    assert any(AMENDED in e and "overlaps" in e for e in errors), errors


def test_a_gap_between_versions_is_refused_and_names_the_key() -> None:
    errors = _version_tree_errors("gap.yaml")
    assert any(AMENDED in e and "gap" in e for e in errors), errors


def test_a_key_may_not_repeat_across_two_instruments() -> None:
    seen: dict[str, str] = {}
    first = validate_instrument_doc(_load(VERSIONS / "repeated_key_a.yaml"), "a.yaml", seen_keys=seen)
    second = validate_instrument_doc(_load(VERSIONS / "repeated_key_b.yaml"), "b.yaml", seen_keys=seen)
    assert first == []
    assert any(AMENDED in e and "a.yaml" in e for e in second), second


def test_a_key_may_repeat_within_one_instrument_as_versions() -> None:
    seen: dict[str, str] = {}
    assert validate_instrument_doc(_load(VERSIONS / "example_a.yaml"), "example_a.yaml", seen_keys=seen) == []


def test_from_without_by_is_refused_and_names_the_key() -> None:
    errors = validate_instrument_doc(_load(VERSIONS / "from_without_by.yaml"), "from_without_by.yaml")
    assert any(AMENDED in e and "'by'" in e for e in errors), errors


def test_by_outside_the_selecting_dates_is_refused_and_names_the_key() -> None:
    errors = validate_instrument_doc(_load(VERSIONS / "unknown_by.yaml"), "unknown_by.yaml")
    assert any(AMENDED in e and "vocab/selecting_dates.json" in e for e in errors), errors


def test_two_versions_starting_on_one_day_are_refused() -> None:
    errors = _version_tree_errors("duplicate_from.yaml")
    assert any(AMENDED in e and "(key, from) must be unique" in e for e in errors), errors


def test_two_undated_rows_of_one_key_are_refused() -> None:
    doc = _load(VERSIONS / "example_a.yaml")
    del doc["obligations"][1]["in_force"]
    errors = resolve.tree_errors([("f.yaml", doc)])
    assert any(AMENDED in e and "no `from`" in e for e in errors), errors


def test_from_after_until_and_an_impossible_date_are_refused() -> None:
    doc = _load(VERSIONS / "repeal.yaml")
    doc["obligations"][1]["in_force"]["until"] = "2027-06-30"
    errors = validate_instrument_doc(doc, "repeal.yaml")
    assert any(AMENDED in e and "from must precede until" in e for e in errors), errors

    doc["obligations"][1]["in_force"] = {"from": "2027-02-30", "by": "event_date"}
    errors = validate_instrument_doc(doc, "repeal.yaml")
    assert any(AMENDED in e and "not a calendar date" in e for e in errors), errors


def test_an_instrument_level_in_force_is_checked_too() -> None:
    doc = _load(VERSIONS / "instrument_level.yaml")
    doc["in_force"]["by"] = "renewal_date"
    errors = validate_instrument_doc(doc, "instrument_level.yaml")
    assert any("fixture_sop_act_wa" in e and "vocab/selecting_dates.json" in e for e in errors), errors


def test_in_force_is_refused_outside_its_four_fields() -> None:
    doc = _load(VERSIONS / "example_a.yaml")
    doc["obligations"][1]["in_force"]["effective"] = "2027-07-01"
    errors = validate_instrument_doc(doc, "example_a.yaml")
    assert any("effective" in e and AMENDED in e for e in errors), errors

