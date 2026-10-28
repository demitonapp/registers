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


def test_a_disease_without_five_causes_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["overrun"]["causes"].pop()
    assert validate_diseases(release) == [
        "vocab/diseases.json: overrun: causes must be five entries, each with key, label and covers"
    ]


def test_a_cause_key_in_two_diseases_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["disputes"]["causes"][0]["key"] = "lapsed"
    assert validate_diseases(release) == ["vocab/diseases.json: cause keys ['lapsed'] belong to more than one disease"]
