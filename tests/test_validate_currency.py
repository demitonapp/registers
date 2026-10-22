"""Currency is data, never a name: no property names a currency, and a currency-code field is
named `currency` or `<amount>_currency`.

    python -m pytest tests/test_validate_currency.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from bump_check import schema_bump_needed  # noqa: E402
from validate import (  # noqa: E402
    UNMIGRATED_CURRENCY_SPELLINGS,
    _walk_currency_names,
    currency_in_name,
    validate,
)


def _walk(properties: dict, contract: str = "demo") -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    _walk_currency_names({"properties": properties}, "#", errors, warnings, Path(f"contracts/{contract}.schema.json"), contract)
    return errors, warnings


@pytest.mark.parametrize("name", ["value_aud", "total_awarded_aud_3yr", "valueAud", "fee_nzd", "price_USD", "gbp_total"])
def test_a_property_naming_a_currency_is_refused(name: str) -> None:
    errors, _ = _walk({name: {"type": "number"}})
    assert len(errors) == 1 and "names a currency" in errors[0]


@pytest.mark.parametrize(
    "name",
    ["value", "claim_amount", "currency", "value_currency", "top_agency_names", "cad_drawing", "lsl_balance", "weight_kgs", "all_day"],
)
def test_a_name_that_only_looks_like_a_code_is_allowed(name: str) -> None:
    assert currency_in_name(name) is None
    assert _walk({name: {"type": "number"}}) == ([], [])


def test_a_nested_property_is_checked() -> None:
    errors, _ = _walk({"lines": {"type": "array", "items": {"properties": {"cost_aud": {"type": "number"}}}}})
    assert len(errors) == 1 and "cost_aud" in errors[0]


@pytest.mark.parametrize("type_", ["currency", "string", "money"])
def test_a_currency_code_field_named_anything_else_is_refused(type_: str) -> None:
    errors, _ = _walk({"currency_code": {"type": type_}})
    assert len(errors) == 1 and "must be named `currency`" in errors[0]


@pytest.mark.parametrize("name", ["currency", "retention_currency", "accounts[].currency"])
def test_the_two_allowed_spellings(name: str) -> None:
    assert _walk({name: {"type": "currency"}}) == ([], [])


def test_an_exchange_rate_is_not_a_currency_field() -> None:
    # `currency_rate` holds a number, not a code, so the spelling rule leaves it alone.
    assert _walk({"currency_rate": {"type": "decimal"}}) == ([], [])


def test_the_unmigrated_spellings_warn_and_nothing_else_does() -> None:
    errors, warnings = _walk({"currency_code": {"type": "currency"}}, contract="bank_accounts")
    assert errors == [] and len(warnings) == 1 and "(unmigrated)" in warnings[0]


def test_the_tree_has_no_currency_error_and_warns_only_on_the_pinned_four() -> None:
    errors, warnings = validate()
    assert [e for e in errors if "currency" in e.lower()] == []
    unmigrated = {w.split(": ")[0].removeprefix("contracts/").removesuffix(".schema.json") for w in warnings if "(unmigrated)" in w}
    assert unmigrated == {c for c, _ in UNMIGRATED_CURRENCY_SPELLINGS}
    # The set may only shrink: pin its size so a new exception is a visible edit to this test.
    assert len(UNMIGRATED_CURRENCY_SPELLINGS) == 4


def test_renaming_an_amount_is_major_and_adding_a_currency_is_minor() -> None:
    old = {"type": "object", "properties": {"value_aud": {"type": "number"}}}
    renamed = {"type": "object", "properties": {"value": {"type": "number"}, "currency": {"type": "currency"}}}
    assert schema_bump_needed(old, renamed) == "major"
    only_added = {"type": "object", "properties": {"value": {"type": "number"}}}
    with_currency = {"type": "object", "properties": {"value": {"type": "number"}, "currency": {"type": "currency"}}}
    assert schema_bump_needed(only_added, with_currency) == "minor"
