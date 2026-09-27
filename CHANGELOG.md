# Changelog

## Unreleased

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
