"""vocab/diseases.json is one taxonomy the obligation rows and the engines agree on.

    python -m pytest tests/test_validate_diseases.py -q
"""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate import validate_diseases  # noqa: E402

RELEASE = json.loads((ROOT / "vocab" / "diseases.json").read_text())


def test_the_published_taxonomy_passes() -> None:
    assert validate_diseases() == []


def test_an_obligation_disease_the_taxonomy_does_not_define_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["order"].remove("disputes")
    del release["diseases"]["disputes"]
    assert any("differs from contracts/obligation.schema.json" in e for e in validate_diseases(release))


def test_a_disease_without_buyer_copy_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["rework"]["prevention"] = " "
    assert validate_diseases(release) == ["vocab/diseases.json: rework: prevention is required"]


def test_a_register_with_no_contract_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["rework"]["feeders"].append("no_such_register")
    assert validate_diseases(release) == ["vocab/diseases.json: rework: register 'no_such_register' has no contract"]


def test_an_order_that_repeats_or_omits_a_disease_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["order"].append("rework")
    assert any("exactly once" in e for e in validate_diseases(release))


def test_a_disease_that_does_not_lie_about_its_five_causes_is_refused() -> None:
    """SM065/P1: five cause categories per disease, and four is a taxonomy with a hole."""
    release = copy.deepcopy(RELEASE)
    release["diseases"]["rework"]["subcategories"].pop()
    assert validate_diseases(release) == [
        "vocab/diseases.json: rework: subcategories must list exactly five cause categories"
    ]


def test_a_cause_key_carried_by_two_diseases_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["overrun"]["subcategories"][0]["key"] = "design_documentation"
    errors = validate_diseases(release)
    assert any("belongs to one disease" in e for e in errors), errors


def test_a_cause_with_no_detector_state_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["disputes"]["subcategories"][0]["status"] = "soon"
    assert any("status must be one of" in e for e in validate_diseases(release))


def test_a_cause_with_no_evidence_register_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["non_compliance"]["subcategories"][1]["evidence"] = []
    assert any("names no evidence register" in e for e in validate_diseases(release))
