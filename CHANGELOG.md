# Changelog

## Unreleased

- New Zealand's Health and Safety at Work Act 2015: `obligations/NZ/hswa_2015.yaml`,
  read in the current version (as at 5 April 2025). Notify WorkSafe NZ as soon
  as possible after a notifiable event (s 56(1)), written notice within 48
  hours when required (s 56(3)(b)), keep the record 5 years (s 57(1)); plus a
  genuinely NZ-specific duty with no AU equivalent - 24 hours' written notice
  before starting defined "notifiable work" (falls, scaffolding, lifts, deep
  narrow excavations), under the still-current Health and Safety in
  Employment Regulations 1995 reg 26.

- Security of payment for SA, TAS, ACT and NT: 26 rows read in each Act's
  current text (`obligations/AU-SA/sop_act_2009_sa.yaml`,
  `AU-TAS/sop_act_2009_tas.yaml`, `AU-ACT/sop_act_2009_act.yaml`,
  `AU-NT/cc_sop_act_2004_nt.yaml`). SA's 2021 amendments never passed; NT's
  West Coast Act has a notice of dispute in place of a payment schedule, and
  a 65 working day adjudication window.
- Notifiable incidents under all eight WHS/OHS Acts (NSW, QLD, SA, TAS, ACT,
  NT, WA and Victoria's OHS Act): notify immediately, written notice within
  48 hours, keep the record 5 years. 24 rows. The Commonwealth Act is left
  out - it binds Commonwealth workplaces, not a state job.

- AS 4902-2000 (design and construct): `obligations/AU/as4902_2000.yaml`, four
  rows read in the full text - EOT claim (cl 34.3), latent conditions notice
  (cl 25.2), claim notice and particulars (cl 41.1-41.3) and the Final Payment
  Claim (cl 37.4).
- Correction, `obligations/AU-QLD/tmr_mrts50.yaml` (March 2025): MRTS50 states
  no 12-month as-constructed deadline. `closeout.as_constructed_records.tmr_mrts50`
  now carries cl 12.1 only (As Constructed drawings before the Certificate of
  Practical Completion, no window); cl 11.2's record retention is its own row,
  `closeout.records_retention.tmr_mrts50`; the nonconformance notice cites
  cl 10.2, not 10.1.1.

- SM030 O23: the first `threshold` obligations. `contracts/obligation.schema.json`
  gains `threshold` (`direction` max or min, `value`, `unit`, `set_by` library
  or org), required on a `threshold` row and refused elsewhere by
  `scripts/validate.py`; `contracts/platform_obligation.schema.json` gains the
  flat `threshold_direction`, `threshold_value`, `threshold_unit`,
  `threshold_set_by`. Three rows: `overrun.budget_tolerance.au` and `.nz` (the
  contractor's own budget tolerance, a labelled 0% default, METHOD.md section
  6.1), and `rework.lot_compaction.tmr_mrts04` and `.tfnsw_r44` (principal
  compaction minimums, recorded `not_collected` until a lot is measured
  against them).
- SM030 O3: `contracts/platform_obligation.schema.json` (the flat shelf-fact
  shape a project's protection reads from, one row per obligation), added
  beside `platform_evidence_standard`, which is now marked
  `x-demiton-deprecated` (superseded, no new rows, history kept per
  METHOD.md rule 4) rather than removed. Same change also finally widens
  `platform_evidence_standard.grade`'s enum to include `demiton_default`
  (MINOR, 1.1.0): the Demiton monorepo's own vendored copy carried this
  member since 2026-09-26 as a stopgap because it "could not go into
  registers_private.json" (that overlay holds private data only) - this
  release is what the seed's own comment called "the next
  scripts/vendor_registers.sh bump" that would bring the two back in sync.
- SM030 O2: `obligations/<jurisdiction>/*.yaml`, 131 obligations across 30
  instruments, transcribed from the evidence-standard register the Demiton
  product's Disputes check reads today. Row-by-row record, including every
  correction and addition, in the Demiton monorepo at
  `docs/instructions/roadmap/work/specs/moat/ux/obligations/library-transcription.md`.
- SM030 O1: `contracts/obligation.schema.json` and `contracts/instrument.schema.json`,
  the `vocab/` directory (sources, instrument types, protection types, diseases,
  jurisdictions, industries), and `scripts/validate.py` extended to check every
  `obligations/<jurisdiction>/*.yaml` instrument against them - the contract for
  the obligation library that SM030 O2 populates next. GOVERNANCE.md now states
  what that tree publishes ("public instruments, not recorded data") and who
  reviews a pull request against it.
- Initial import (spec 09 P2): 171 register contracts and 482 historical
  versions from the Demiton monorepo's `platform.shelf_schema` registry, plus
  three disease-economics research schemas (finding, source, protection).
  A fourth, organisation (the publisher-independence register), follows once
  its own notice period there completes. See [09a-p0-register-reconciliation.md](https://github.com/demitonapp/monorepo/blob/staging/docs/instructions/roadmap/specs/moat/ux/onboarding-by-contract/09a-p0-register-reconciliation.md)
  for exactly what was and wasn't brought across, and why.
