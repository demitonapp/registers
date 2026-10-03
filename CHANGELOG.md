# Changelog

## Unreleased

- **`platform_obligation` 1.2.0**: declares the five fields the projection already
  writes: `approval_class`, `trigger` and `trigger_event` (the trigger's resolved
  catalogue entry), and the engine-routing `measure` and `anchor`. A consumer that
  compares a stored row with a new one through this contract ignores an undeclared
  key present on one side only, so none of the five ever reached a row stored before
  it existed (found in Demiton SM038/X0's review). MINOR: five new optional
  properties.
- **Public holiday calendars** (`holidays/`): all eight Australian states and
  territories, 2025 to 2027 (NT 2026 to 2027: no complete 2025 list of its show
  days was found). Each date was read from the Fair Work Ombudsman's yearly lists
  and checked against the state's own page; each file cites its holidays Act.
  Flagged, because security of payment Acts count them differently: area-only days
  (`localities_vary`: Melbourne Cup, WA King's Birthday, NT show days, and every
  Tasmanian Schedule 1 and 2 local day, which TAS SOP Act s 4A(2) counts
  statewide), part-day (`part_day`) and bank-only days (`bank_holiday`: the ACT's
  first Monday in August). Left out, and named in each file's `not_included`:
  evening part-days, other states' show days and one-area holidays, and NSW's
  bank-only day. Victoria's 2027 AFL Grand Final Friday is not yet set and is
  published as a range. `validate.py` checks the new tier; the obligations
  release asset now carries `holidays/`.
- **Event types narrowed to the event each clause names** (Demiton SM038). Three
  v5 types matched every record in their register, while the clauses citing them run
  from something narrower: `incident_recorded` is replaced by
  `notifiable_incident_recorded` (`safety_incident.notifiable` is true) and
  `written_notice_required` (dated by `safety_incident.written_notice_required_at`:
  model WHS Act s 38(4) and HSWA s 56(3)(b) run from the regulator's requirement,
  not from the incident), and `ncr_raised` by `notifiable_ncr_raised`
  (`safety_ncr.notifiable` is true, MRTS50 cl 10.2). Retargeted: 10 flattened duties
  to `notifiable_incident_recorded` (every state's `whs.incident_notice`, and VIC's
  written record, which s 38(3) runs from the duty to notify), 8 to
  `written_notice_required`, 1 to `notifiable_ncr_raised`. Still 31 triggered duties.
  A record whose `date_field` is empty is not an event of that type. `validate.py`
  now refuses a `match` value its field can never hold (a string against a boolean,
  a value outside an enum), which would otherwise start no clock at all.
- **`safety_ncr` 2.1.0**: an optional `notifiable`, true when a nonconformance meets
  a notification trigger in the contract that governs it (MRTS50 cl 10.2 (a) to (j)).
  MINOR: a new optional property.
- **`safety_incident` 2.1.0**: an optional `notifiable` (a death, a serious injury or
  illness, or a dangerous incident: model WHS Act ss 35-37, OHS Act 2004 (Vic) s 37,
  HSWA 2015 (NZ) s 25) and an optional `written_notice_required_at` (when the
  regulator required written notice). MINOR: two new optional properties. No source
  system fills either yet; until one does, an incident starts no notification clock.
- **`compliance_evidence` 2.1.0**: `rejected_by` and `rejected_at`, so a
  rejection no longer writes its decider into `approved_by` and `approved_at`.
  Those two now mean approved and nothing else. MINOR: two new optional
  properties.
- `compliance_evidence` 2.0.0 (MAJOR): evidence a person uploads now carries
  four eyes. Ten optional fields: `media_kind` (`photo`, `document`),
  `media_sha256`, `submitted_by` and `submitted_at`, `approval_state`
  (`submitted`, `approved`, `rejected`), `approved_by` and `approved_at`,
  `rejection_reason`, `captured_at`, `captured_on_site`. MAJOR because of one
  new requirement: `approval_state` is required whenever `media_kind` is set
  (`allOf` if/then). A row from a connected system carries no `media_kind`, so
  every row such a system wrote still validates; the system is its second pair
  of eyes. A reader counts an uploaded row only once it is `approved`, by someone
  other than its submitter. 1.0.2 is kept in `history/`.
- `bump_check.py` now calls a requirement added under `allOf`, `then` or
  `else` MAJOR when the document it binds already existed. It used to skip any
  `required` list at a new location, the rule meant for a property that is
  itself new, so `if media_kind then required approval_state` read as MINOR
  although a document carrying `media_kind` alone stops validating. A
  requirement under `if` still counts for nothing, since failing an `if`
  invalidates no document. First tests for the script: `tests/test_bump_check.py`.
- **`site_diary` 1.1.0**: an optional `kind` on each `delays` entry (`weather`,
  `latent_condition`, `direction`, `access`, `supply`, `other`), so a latent condition
  written in a diary can start its own clock (Demiton SM038 decision 6). MINOR: a new optional property. No source system fills it yet.
- **An event-type catalogue and `trigger` on obligations** (contract `obligation`
  2.2.0, MINOR). `vocab/event_types.json` defines the events that
  start an obligation's clock: `claim_lodged`, `machine_started`, `incident_recorded`,
  `ncr_raised`, `delay_recorded` (any diary delay), `latent_condition_reported` (a diary
  delay of kind `latent_condition`). Each names its
  register, date field, subject (project, asset, worker or reference) and, where the
  proof names its trigger, the proof's reference field. Not a register of events: the
  events stay facts in their own registers. 19 source rows carry a `trigger` (31
  flattened duties: every state's payment-schedule and incident-notice rows share one
  definition each). `validate.py` refuses a trigger not in the catalogue and a
  catalogue entry naming a register or field that does not exist. **Review:** the
  `machine_started` match value (`event_type: ignition`).

- **High risk work licence duties (QLD, NSW) and a subcontractor insurance
  default**. The first two concretes of the competency shape:
  Work Health and Safety Regulation 2011 (Qld) and 2025 (NSW), s 81 (hold the
  licence) and s 85 (the business must see written evidence of it before the
  work), graded `primary_via_secondary`: sections confirmed through published
  text quoted by AustLII and legislation-site summaries, not a full read of the
  Part. And `own_commitments.subcontractor_insurance_current.au`, a labelled
  Demiton default (METHOD.md 6.1) checking a subcontractor's certificate of
  currency is in date. 247 to 252 flattened rows.

- **`approval_class` on every obligation** (contract `obligation` 2.1.0, a MINOR
  bump: a new optional property). `vocab/approval_classes.json` fixes six classes
  (geotechnical, quality, safety_environment, variations_claims, payments,
  general); every base and standalone row names one, overrides inherit it, and
  `resolve.tree_errors` refuses a resolved row without one. It says what kind of
  sign-off a row's evidence needs, so a consumer can route an approval through
  its own delegation of authority (Demiton SM037). Proposed classes for all 247
  flattened rows: payments 112, safety_environment 69, variations_claims 53,
  quality 9, general 2, geotechnical 2. **Every class is a proposal for review.**
- **`plant_registration` 2.1.0**: an optional `expires_on`, so a check can flag a
  registration before it lapses (Demiton SM035 rows 12 and 24).
  MINOR: a new optional property.

- CLOCS-A, the construction logistics heavy vehicle standard (v1.6, 21 April
  2026): `obligations/AU/clocs_a_standard.yaml`, 14 rows read in the Standard's
  own text. Principal Contractor duties (six-monthly risk register review, CLMP
  updated within 1 month of a change, traffic management plan, driver licence,
  training and induction, incident investigation, quarterly reporting) and
  Transport Operator duties (vehicle safety equipment by tier, daily pre-start,
  licence checks, speed and harsh-driving monitoring, quarterly reporting).
  CLOCS-A is voluntary (s 1): it binds a contractor only when the client's
  contract requires it (s 3), which every row's caveat says. Windows are
  recorded only where the Standard states a number; it states none for
  incident notification, licence checks, refresher training or retention.
- Portable long service levies across every AU state and territory (8 rows,
  1 per jurisdiction, `levy.*`), read in each Act's current text. Two
  families: project-value levies payable before work starts (QLD, NSW, NT -
  liability falls on the permit applicant or person for whom the work is
  done, often the principal rather than the contractor, so framed as a
  check) and wage-based recurring employer levies (VIC, WA, SA, ACT, TAS).
  Two corrections to the research brief this replaces: QLD's Act was never
  replaced by a 2020 Act (still the 1991 Act, current as at 1 Feb 2024), and
  Tasmania does have a scheme (TasBuild) - it just has no standalone rate in
  its own Act, since its levy power rides on a separate Training Fund Act.
  Current rates and project-value thresholds mostly sit in each state's
  Regulation, not its Act, so are recorded from the authority's own site
  where cited, not asserted as primary-read.

- New Zealand's Health and Safety at Work Act 2015: `obligations/NZ/hswa_2015.yaml`,
  read in the current version (as at 5 April 2025). Notify WorkSafe NZ as soon
  as possible after a notifiable event (s 56(1)), written notice within 48
  hours when required (s 56(3)(b)), keep the record 5 years (s 57(1)); plus a
  genuinely NZ-specific duty with no AU equivalent - 24 hours' written notice
  before starting defined "notifiable work" (falls, scaffolding, lifts, deep
  narrow excavations), under the still-current Health and Safety in
  Employment Regulations 1995 reg 26.
- Victoria's SOP Act re-read in Authorised Version 015 (as at 24 June 2026,
  after No. 43/2025). `payment.due_date.au-vic` corrected: a contract cannot
  set payment later than 20 business days after the claim (s 12(1B)); the
  default is 10 business days after the earliest day a claim may be served,
  not after a schedule. Claims now need the prescribed form (s 14(2)). Two
  new rows: 5 business days' notice before recourse to a performance
  security (s 17H), and the window for claiming a security's release
  (s 17A-17C).
- GC21 Edition 2 (NSW): three rows it shares with TfNSW's amended form -
  Contract Program within 14 days (cl 22.1), statutory change notice within
  7 days (cl 49.1, 49.4), Final Payment Claim within 13 weeks (cl 61.1).
- `obligations/AU-NSW/tfnsw_c2_gc21.yaml`: TfNSW's C2-GC21 Ed 2 Rev 19
  (form `TFNSW_GC21`). Its windows match plain GC21 on every duty above;
  the one duty only it carries is the subcontractor proof of payment
  procedure (cl 28.3, 28.4, Schedule 17) - pay within 3 business days,
  prove within 5.
- `contract_terms` 1.3.1 (PATCH): `contract_form`'s vocabulary gains
  `TFNSW_GC21`, Transport for NSW's amended GC21 (C2-GC21). Its duties are
  plain GC21's plus TfNSW's own; a TfNSW contract is no longer read as plain
  GC21. 1.3.0 kept in `history/`.
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
