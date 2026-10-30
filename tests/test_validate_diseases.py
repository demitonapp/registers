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
    release["diseases"]["overrun"].pop("i18n", None)  # its translation names the cause removed
    release["diseases"]["overrun"]["causes"].pop()
    assert validate_diseases(release) == [
        "vocab/diseases.json: overrun: causes must be five entries, each with key, label and covers"
    ]


def test_a_cause_key_in_two_diseases_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["disputes"].pop("i18n", None)  # its translation names the cause renamed
    release["diseases"]["disputes"]["causes"][0]["key"] = "design_documentation"
    assert validate_diseases(release) == ["vocab/diseases.json: cause keys ['design_documentation'] belong to more than one disease"]


def test_a_translation_of_an_unknown_cause_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["rework"]["i18n"]["fr"]["causes"]["lapsed"] = {"label": "Expiré", "covers": "x"}
    assert validate_diseases(release) == [
        "vocab/diseases.json: rework: i18n.fr: cause 'lapsed' is not one of rework's causes"
    ]


def test_a_translated_field_that_is_not_copy_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["rework"]["i18n"]["fr"]["lable"] = "Reprises"
    assert validate_diseases(release) == ["vocab/diseases.json: rework: i18n.fr: lable is not a translated field"]


def test_an_empty_translation_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["overrun"]["i18n"]["fr"]["what"] = " "
    assert validate_diseases(release) == ["vocab/diseases.json: overrun: i18n.fr: what must be non-empty text"]


def test_a_language_that_is_not_a_two_letter_code_is_refused() -> None:
    release = copy.deepcopy(RELEASE)
    release["diseases"]["disputes"]["i18n"]["fr-FR"] = release["diseases"]["disputes"]["i18n"].pop("fr")
    assert validate_diseases(release) == [
        "vocab/diseases.json: disputes: i18n.fr-FR: the language must be a two-letter code other than en"
    ]


def test_a_partial_translation_is_allowed() -> None:
    release = copy.deepcopy(RELEASE)
    del release["diseases"]["rework"]["i18n"]["fr"]["prevention"]
    del release["diseases"]["rework"]["i18n"]["fr"]["causes"]["scope_change"]
    assert validate_diseases(release) == []
