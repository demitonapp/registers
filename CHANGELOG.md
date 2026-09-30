# Changelog

## Unreleased

- The contractor's own repeat-purchase line
  (`obligations/AU/demiton_repeat_purchase.yaml`). One row: an item a job
  re-buys that its plan did not carry is rework, and an item bought across
  three or more distinct jobs is a routine consumable. `set_by: org` with a
  labelled 3-job default; the value an org chooses at switch-on is never
  published.
- SM031: an obligation can `extends` an abstract base, so shared law is written
  once. `contracts/instrument.schema.json` and `contracts/obligation.schema.json`
  move to 2.0.0: `abstract` and `model_type` describe a base under
  `obligations/_model/`, `extends` points a concrete at one, and `grade` gains
  `inherited` (a row instantiated from a base without re-reading that
  jurisdiction's own text) and is no longer schema-required, because a base may
  leave the grade to the concrete that first reads it. The new
  `contracts/obligation_override.schema.json` is the row shape inside an
  extending concrete: it names its base obligation in `overrides`, carries the
  flattened row's own `key`, and refuses a forbidden field (`duty`,
  `consequence`, `protection_type`, `disease`, `severity`, `evidence`) with
  `additionalProperties: false`. `contracts/platform_obligation.schema.json`
  widens its `grade` enum to 1.1.0 so a shelf fact can carry `inherited`.
  `scripts/resolve.py` is new - it flattens the tree, and `scripts/validate.py`
  imports its tree checks so the checks and the flattening cannot drift. Both
  version bumps are taken as MAJOR deliberately; the computed bump is MINOR,
  because nothing that validated before stops validating, and the deliberate
  part is that an `obligations` array may now hold overrides.
- SM031: the model WHS Act and the model WHS Regulations are held once. Seven
  WHS/OHS Acts (ACT, NSW, NT, QLD, SA, TAS, WA) carried the same three
  notifiable-incident duties word for word, and four WHS Regulations (ACT, NSW,
  QLD, SA) carried the same excavation-record duty. They now extend
  `model_whs_act_2011` and `model_whs_regulations_2011`; each keeps its own key,
  citation and publisher, and the notice duty keeps its own caveat because the
  states' penalties and exclusions differ. The flattened obligations are
  unchanged: 196 before, 196 after, row for row.
- SM031: ten shared-shape bases give the four empty sources a shape to
  instantiate from. `approvals` gains an environmental authority, a waterway
  barrier, vegetation clearing and Aboriginal heritage shape; `counterparties`
  an insurer-notification shape; `workforce` the construction award and the
  enterprise agreement; `own_commitments` prequalification, certification and
  competency. Each carries the duty, consequence, protection type, disease,
  severity and evidence register a concrete will inherit, and states no clause
  and no `grade`, because the shape is drawn across instruments rather than read
  from one - the concrete that first reads its own state's text supplies both.
  Bases add no obligations of their own, so the flattened count stays 196.
  [obligations/README.md](obligations/README.md) is new and states the tiers,
  what an override may supply, and what the checks refuse.
- SM031 M6: the sources that were empty now have their first instruments.
  `approvals` (Queensland): an environmental authority under the Environmental
  Protection Act 1994 (s 430, contravening a condition; s 320DA, regulator
  notification in 24 hours), a waterway barrier works approval under the
  Fisheries Act 1994 (s 76T, the development permit; s 76U, the fish-way
  conditions), a vegetation clearing development approval under the Planning Act
  2016 (s 163, assessable development without a permit; s 164, compliance with
  the approval), and Aboriginal cultural heritage under the Aboriginal Cultural
  Heritage Act 2003 (ss 23-24, the duty of care and unlawful harm).
  `workforce`: the Building and Construction General On-site Award 2020
  (MA000020, cll 19, 21-23, 30). `own_commitments`: the National Prequalification
  System for Civil (Road and Bridge) Construction Contracts, November 2024
  (cl 6.2, maintaining status by submitting regular and full updates; cl 8.5,
  advising the department in writing immediately of a change of circumstances).
  Each adopts only the duties its own instrument states, and the duties it does
  not carry are not adopted: an environmental authority's records; a general
  conditions duty where the Fisheries Act reaches only fish-way conditions; the
  Vegetation Management Act's register (the chief executive's, not the
  contractor's); the Aboriginal Cultural Heritage Act's find-reporting duty,
  which the Act does not state; the award's employee-record duty, which is a Fair
  Work Regulation; and the prequalification shape's separate records duty. The
  flattened set grows from 196 to 213. New South Wales is read through the
  Internet Archive's copies of the government's own whole-Act page and XML
  export, because `legislation.nsw.gov.au` and `classic.austlii.edu.au` both
  answer HTTP 403 from the build environment: an environment protection licence
  under the Protection of the Environment Operations Act 1997 (s 64,
  contravening a condition; s 148, immediate notification of a material-harm
  incident), Aboriginal objects and places under the National Parks and Wildlife
  Act 1974 (s 86, harm; s 89A, notification within a reasonable time), an
  in-water works permit and fish passage under the Fisheries Management Act 1994
  (s 201, the ministerial permit; ss 218-219, fishways and passage not to be
  blocked), and native vegetation clearing under the Local Land Services Act
  2013 (ss 60N, 60ZF). The NSW clearing regime is the Local Land Services Act,
  not the Biodiversity Conservation Act the spec named, because that is where
  the offence and the Panel approval live. Two rows clear a window the base
  states - `approvals.aboriginal_heritage_find.au-nsw` and
  `approvals.environmental_authority_incident_notice.au-nsw` - because "within a
  reasonable time" and "immediately" are not fixed periods, and
  `obligation_override.schema.json` now lets an override set a window to null for
  that case. **One bucket stays empty:** `counterparties`, because an insurer's
  notification clause lives in the policy a given org holds and no single
  national instrument carries it - which is what this spec's own Files bullet
  anticipated ("where a single national instrument applies").
- TfNSW TS 00088 Minimum Requirements for Contractor Vehicles (1.0, effective
  26 August 2025, not retrospective): `obligations/AU-NSW/tfnsw_ts00088.yaml`,
  6 rows - registration for the contract (cl 5.1), SafeWork plant registration
  (cl 5.4), operating information (cl 6.8), the operator's daily inspection
  before each shift and service records (cl 6.9), and at least CLOCS-A Bronze
  equipment on heavy vehicles, or the tier the contract manager selects (cl 8,
  Table 1). Keyed to TfNSW's amended GC21, the same judgment call as G2-C2.

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
