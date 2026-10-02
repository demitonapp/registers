"""The holiday-calendar tier refuses what a consumer would misread.

    python -m pytest tests/test_validate_holidays.py -q
"""
from __future__ import annotations

import copy
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

from validate import holiday_calendar_files, validate_holiday_calendar  # noqa: E402

QLD = yaml.safe_load((ROOT / "holidays" / "AU-QLD.yaml").read_text())


def test_every_state_and_territory_has_a_calendar_that_passes() -> None:
    files = holiday_calendar_files()
    assert sorted(p.stem for p in files) == ["AU-ACT", "AU-NSW", "AU-NT", "AU-QLD", "AU-SA", "AU-TAS", "AU-VIC", "AU-WA"]
    for path in files:
        assert validate_holiday_calendar(yaml.safe_load(path.read_text()), path.name, path.stem) == []


def test_a_date_outside_the_listed_years_is_refused() -> None:
    # `years` promises completeness; a 2028 date in a 2025-2027 file would let a
    # consumer believe the rest of 2028 is known.
    doc = copy.deepcopy(QLD)
    doc["holidays"].append({"date": "2028-01-03", "name": "New Year's Day (additional)"})
    assert any("2028-01-03" in e for e in validate_holiday_calendar(doc, "AU-QLD.yaml", "AU-QLD"))


def test_a_file_named_for_another_state_is_refused() -> None:
    assert any("declares" in e for e in validate_holiday_calendar(QLD, "AU-NSW.yaml", "AU-NSW"))


def test_an_unquoted_yaml_date_is_refused() -> None:
    # yaml loads 2026-10-05 as a date object; the schema wants the string.
    doc = copy.deepcopy(QLD)
    doc["holidays"][0]["date"] = yaml.safe_load("2026-10-05")
    assert validate_holiday_calendar(doc, "AU-QLD.yaml", "AU-QLD")
