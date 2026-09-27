# Changelog

## Unreleased

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
