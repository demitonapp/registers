# Changelog

From the next tag on, each release has its own section, headed
`## vN, YYYY-MM-DD: <kinds>`: the tag, its date, and every kind of change it
carries, `addition` (a new instrument, a jurisdiction switched to supported, or a
new duty: it ships with the release), `amendment` (a rule in force from a date
after the tag) or `correction` (a row that was wrong). Releases are cut and
deployed when needed; there is no fixed cadence. `scripts/release_kind.py`
computes the kinds from the diff against the previous tag, and the release
workflow refuses a tag whose section does not declare every one. Cutting a tag
turns `## Unreleased` into that section. v18 is the first tag cut this way;
`## v17 and earlier` holds every bullet from v1 to v17, text unchanged (v17,
MRTS50's seven rows, was cut before this rule and declared a correction).

## Unreleased

- Release gate, re-review fixes (SM052/D5). `scripts/release_kind.py` read only the obligation library, so a release carrying only a holiday-calendar correction computed `none` and shipped with no digest. It now compares every `holidays/` file by parsed content between the two tags: a calendar that only gains holidays in years it did not list (its other fields unchanged, `sources` may grow), or a new file, is an `addition`; any other change (a changed or removed date, a date added to a year the file already listed as complete, a changed field, a removed file) is a `correction`, keyed by the file and with the file in its reason. A jurisdiction switched from supported to unsupported in `vocab/jurisdictions.json` is a `correction` (only a switch on was counted). Both are computed kinds, so the tag's CHANGELOG heading must declare them. Two `## vN` headings for one tag are refused (the first used to win silently), and an impossible heading date such as `2026-13-45` is a refusal message, not a traceback. `RELEASE.json` and the flattened library are unchanged (v29 computes the same).

## v29, 2026-10-23: no obligation kinds (register contracts only)

- Dated versions, review fixes (SM052/D1). `until_by`, which `scripts/resolve.py` writes onto an earlier version whose own `by` differs from the next version's, is now declared in the contracts it appears in (`obligation` 2.5.0, `instrument` 2.3.0, `obligation_override` 1.2.0, MINOR each: one new optional derived property), so flattened output passes them; it is derived and never authored, and `scripts/validate.py` refuses it in source YAML. The validator also refuses `removed: true` together with `in_force` (the resolver dropped the block silently; a repeal is an `until` on the last version), and a row that dates itself inside an instrument dated with a `from` unless it keeps the instrument's `by` and starts no earlier (a row's own block replaces the instrument's, so an event-dated amendment row dropped a contract-date floor). `validate.py` now checks the flattened output of the real tree against the contracts. `history/contract_terms/1.5.0.schema.json` is added (v26 shipped 1.5.0; its history copy was missing) and its `history/manifest.json` entry carries the real commit time, in sorted position. No row is dated; the flattened library is unchanged.
- Release gate, review fixes (SM052/D5). The tag date is the date in the tag's `## vN, YYYY-MM-DD: <kinds>` heading, not the runner's UTC clock: `scripts/release_kind.py` uses it as `--on`, and refuses the tag when it differs from the tag commit's date in Australia/Brisbane (`--commit-date`, which the release workflow passes from `git log -1 --format=%cI`). A commit at 22:00 UTC on 1 November is 2 November in Brisbane. Without `--tag`, `--on` defaults to today in Brisbane. An amendment starting fewer than 20 business days after the tag date is now warned once per amendment (it printed twice: once for the new version, once for the earlier version's derived `until`), as a GitHub `::warning::` annotation, in `RELEASE.json` as a new field `warnings: [str]` (`[]` when none; the other fields are unchanged) and in the GitHub release notes under "Late amendments". `validate.yml` runs on `main` only, and its comments and `release.yml`'s no longer mention `next`, waves or `wave_on`.

## v28, 2026-10-23: no obligation kinds (register contracts only)

- Every currency field is type `currency`. Eight contracts declared theirs as `money` (`profit_and_loss`, `budget_vs_actual`, `cost_element`, `expense_claims`, `gl_journal_entry`) or `string` (`contract_penalty` `rate_currency`, `contract_terms`, `platform_research_finding`), so the fact gate did not check the code and the upgrade hops did not normalise it. Each retype is MAJOR (the contract's next major version); no field is renamed or added, and every value that was a currency code stays one. `profit_and_loss` and `budget_vs_actual` also drop a description that said the field names hard-code AUD, which stopped being true in v23.

## v27, 2026-10-23: no obligation kinds (register contracts only)

- `history/manifest.json` dates `platform_research_finding` 2.0.0, the version v24 added without a manifest entry (2026-10-22, the commit that added the history copy). A consumer that requires a release date for every history version, as the monorepo's `test_contract_versions` does, refused v25 and v26 over the gap. No contract changes.

## v26, 2026-10-23: no obligation kinds (register contracts only)

- Dated versions of an obligation. An obligation, an override and an instrument may carry an optional `in_force` block, `{from, until, by, transitional}` (`obligation` 2.4.0, `obligation_override` 1.1.0 and `instrument` 2.2.0, MINOR each): `from` and `until` are the first and last day a version is in force, `by` names the date that decides it, and `by` is required whenever `from` or `until` is present. A new vocabulary, `vocab/selecting_dates.json`, holds the two dates the engine can read, `contract_date` and `event_date`; `scripts/validate.py` refuses any other. The old and the new rule of one duty are now two rows of one key in one file: `scripts/resolve.py` copies an instrument's `in_force` onto each of its rows that states none, sorts the versions of a key by `from` (a row with none is `original`) and derives each earlier version's `until` and `by` from the next version's `from` and `by`. `scripts/validate.py` refuses a key that repeats across two instruments, two versions with one `from`, an `until` on any version but the last (an overlap or a gap), versions that differ in `protection_type`, `disease`, `evidence.register` or `duty_shape`, and a `from` after its `until`; every message names the key. No row is dated in this change, and the flattened library is byte-identical. `scripts/release_kind.py` now reads real version ids: a newly dated version whose `from` is after the tag date is an `amendment`, on or before it a `correction`, and the `until` the resolver derives onto the version before it is not a changed field of that version.
- `platform_obligation` 1.4.0 (MINOR) declares the five fields a dated version of an obligation projects: `obligation_version`, `in_force_from`, `in_force_from_by`, `in_force_until`, `in_force_until_by`. No row is dated yet, so every stored row reads `original` with no bound.
- **`contract_terms` 1.5.0**: adds `contract_date`, the date the contract was entered into (`format: date`, optional, never defaulted). A duty whose rule changed on a date for contracts entered into on or after it (an Act's transitional provision) is selected by this date, so a job with none cannot be measured on it. MINOR: one new optional property. 1.4.0 kept in `history/`. Pairs with the `in_force` block on obligations, whose `by: contract_date` reads it.

## v25, 2026-10-23: no obligation kinds (register contracts only)

- The last currency spellings are renamed (MAJOR on five contracts, 3.0.0 each). `bank_accounts` and `invoice_issued` `currency_code`, and `customer_list` and `vendor_list` `default_currency_code`, become `currency`; `credit_note` `currency_rate`, an exchange rate and not a currency code, becomes `exchange_rate`. `scripts/validate.py` no longer carries a list of tolerated spellings: a currency field not named `currency` or `<amount>_currency` is an error.

## v24, 2026-10-22: no obligation kinds (register contracts only)

- The disease taxonomy is one flat file. `vocab/diseases.json` grows from a key-to-label map to `{ "order": [...], "diseases": { "<key>": { "label", "buyer_name", "what", "prevention", "start", "feeders" } } }`: for each of the five diseases, its label, the buyer copy (the plain name, what it is, what prevention means), the register groups its daily check needs before it can run (`start`, every group must hold data, any one register in a group is enough) and the registers that enrich a verdict (`feeders`), in the order published research says each costs a contractor, most first. The keys are unchanged. `disputes` also carries its `dispute_types`. `platform_research_finding` 2.0.1 (PATCH) describes `disease_key` in these keys instead of Demiton's measure names. `scripts/validate.py` now refuses a taxonomy that disagrees with `obligation.schema.json`'s `disease` enum or names a register with no contract.

## v23, 2026-10-22: no obligation kinds (register contracts only)

- Currency is data, never a name. Eleven contracts drop their currency-named property for the amount plus a `currency` field (MAJOR, the contract's next major version): `plant_fuel_usage` `claim_amount`, `evidence_gap_verdict` `exposure`, `tendered_budget` `total` and `grand_total`, `platform_contractor_stats` `total_awarded_3yr`, `job_budget` `total_budget`, `cash_position` `total_cash`, `market_intelligence` `total_value`, `bid_no_bid_verdict`, `platform_award`, `platform_planning` and `platform_tender` `value` (and `value_min`, `value_max`). `currency` is required where the amount was, optional where it was. `variations` 1.2.0, `project_performance_record` 2.1.0, `maintenance_record` 2.1.0, `margin_watch_learning` 1.1.0 and `punch_list` 1.1.0 gain an optional `currency` (MINOR); `profit_and_loss`, `budget_vs_actual` and `purchase_order` drop their `AUD` unit annotation (PATCH). `scripts/validate.py` now refuses a property whose name carries an ISO 4217 code, and a currency-code field not named `currency` or `<amount>_currency`; four existing fields (`currency_code` on `bank_accounts` and `invoice_issued`, `default_currency_code` on `customer_list` and `vendor_list`) warn until they are renamed.

## v22, 2026-10-21: addition, correction

- **addition** `whs_general_regulations_2022_wa` (Work Health and Safety (General) Regulations 2022 (WA), as at 1 July 2026), `whs_regulations_2022_tas` (Work Health and Safety Regulations 2022 (Tas), authorised as at 1 July 2025) and `whs_nul_regulations_2011_nt` (Work Health and Safety (National Uniform Legislation) Regulations 2011 (NT), as in force at 17 July 2026): 8 rows each, the seven SWMS duties (rr 299 to 303, 312) and the underground services record (r 304), as concretes of the model WHS Regulations, read 2026-10-21. WA r 292 defines a construction project by headcount (5 or more persons at once, no cost threshold); NT r 292 is $1,000,000 and NT r 291 sets a 3 m fall height for residential construction work (19 kinds); Tasmania matches the model. The library now holds the SWMS duties for all eight Australian states and territories.
- **addition** `high_risk_work_licence_whs_general_regulations_2022_wa`, `high_risk_work_licence_whs_regulations_2022_tas` and `high_risk_work_licence_whs_nul_regulations_2011_nt`: 2 rows each, the high risk work licence duties (rr 81 and 85), the Qld and NSW pattern.
- **correction** the model WHS Regulations' `latent_conditions.utility_check` caveat said NT, TAS and WA "almost certainly" carry the duty but could not be pinned; it now says they do, read 2026-10-21. Changes the caveat on the ACT, NSW, Qld and SA rows.

## v21, 2026-10-21: addition, correction

- **addition** `clocs_a_standard` (CLOCS-A Standard v1.6): 16 rows, the Bronze Transport Operator duties in cl 5.4 the library did not carry (5.4.1(a), 5.4.4(a), 5.4.5(a)-(b), 5.4.6(a)-(d), 5.4.7(a)-(c) and (e), 5.4.8(a)-(b), 5.4.9(b), 5.4.10(a)), read 2026-10-21. With the five clauses already held, the library now carries all 21 Bronze cl 5.4 requirements. 13 new duty shapes; the licence, training and incident rows share the Principal Contractor's shapes.
- **correction** `clocs_a.vehicle_safety_spec.au`: the caveat now states each of the 16 Appendix E1 Bronze items in its own sentence, both either/OR pairs and the three city-and-urban items, and what Silver and Gold add, in place of "among others". Re-read 2026-10-21.
- **addition** `clocs_standard_gb` (CLOCS Standard, Version 5, November 2024): 25 rows, jurisdiction GB. The client duties (4.1 to 4.5), the principal contractor duties (5.1 to 5.13, with 5.13 as `guidance`) and the fleet operator duty (7.1, the FORS Silver benchmark). The logistics plan, traffic management plan, client reporting and incident rows share the CLOCS-A shapes, so the two schemes read side by side. 16 new duty shapes.

## v20, 2026-10-20: addition

- **addition** `rail_safety_national_law_au` (Rail Safety National Law (South Australia) Act 2012): 26 rows, jurisdiction AU. Covers accreditation, the safety management system, notifiable occurrences, rail safety workers, the interface agreements a signalling change touches, the 28-day notice before adopting a changed design safety standard, and the interoperability management plan. The two change hooks are the ones a signalling project meets first. Consumed by the `/railways` hub and the four `/australia/railways` chapters in demitonapp/monorepo.
- **Germany: building contract, payment and site law, in German.** Eight instruments under `obligations/DE/`, `DE-BY/` and `DE-NW/`,
  53 rows, each carrying `lang: de` and read on 2026-10-18: the BGB's building
  contract law (30 days after a change request before the client may order it,
  80% of an offered variation price billable on account, deemed acceptance,
  30 days to object to a final invoice, security for the price under s 650f), the
  VOB/B 2016 standard form (12 Werktage to start work and to send the final
  invoice, 21 days for an interim payment, 30 for the final, 28 days to reserve
  claims, 4 years of defect liability; it binds only where the contract adopts it,
  and every row says so), the Baustellenverordnung (14 days' advance notice), the
  Arbeitnehmer-Entsendegesetz and the Mindestlohngesetz (guarantor liability for a
  subcontractor's wages), and on site Bavarian and North Rhine-Westphalian
  heritage law (report a find, leave it for a week, permits and who pays) and
  North Rhine-Westphalia's ordnance ordinance. New jurisdictions `DE-BY` and
  `DE-NW` (`level: state`, `supported: false`); `DE` stays `supported: false`:
  the law is here to be read, and no project can be placed in Germany yet.
  25 new duty shapes. The VOB/B counts Werktage (Monday to Saturday); the library
  has no such unit, so those windows are in calendar days (12 Werktage as 14), with
  the direction of the error stated in each row.

- **France: public works conditions, payment and site law, in French.** Eleven instruments under `obligations/FR/`, 51 rows,
  each carrying `lang: fr` and read on Légifrance on 2026-10-18: the
  CCAG-Travaux 2021 (15 days to object to an ordre de service, 30 days to answer
  the décompte général, 6 months to sue), the Code de la commande publique
  (payment within 30 days, interest at the ECB rate plus 8 points, the 40 euro
  indemnity, the avance, direct payment of subcontractors, the 5% retenue de
  garantie), the loi du 31 décembre 1975 on subcontracting, the loi du
  16 juillet 1971 on retention, the Code civil (art. 1799-1, the payment
  guarantee), the Code de commerce (L. 441-10, private payment periods), and on
  site the DT-DICT (Code de l'environnement), the carte BTP, the obligation de
  vigilance and the PPSPS (Code du travail), the accident declaration within
  48 hours (Code de la sécurité sociale), archaeological finds (Code du
  patrimoine) and décennale insurance (Code des assurances). `FR` was already
  in the vocabulary and stays `supported: false`. 17 new duty shapes, their
  titles in English like every other shape.

- **Washington State's payment, lien and site law.**
  Eleven instruments under `obligations/US-WA/`, 51 rows, every one read from
  app.leg.wa.gov on 2026-10-18: prevailing wages (RCW 39.12: the statement of
  intent before any payment, the affidavit before retainage is released,
  certified payroll monthly), retainage on public works (RCW 60.28: 5%, released
  60 days after completion), the contractor's bond (RCW 39.08: a claim within
  30 days of completion and acceptance), mechanics' liens (RCW 60.04: record
  within 90 days, foreclose within 8 months), public works subcontractor payment
  within 10 days and apprentice utilization (RCW 39.04), interest on unpaid
  public contracts (RCW 39.76), underground utility locates (RCW 19.122),
  archaeological sites, Indian graves and human remains (RCW 27.53, 27.44,
  68.50.645), injury reporting within 8 and 24 hours (WAC 296-27), WISHA
  citation appeals (RCW 49.17) and contractor registration (RCW 18.27). New
  jurisdiction `US-WA` (`level: state`, `supported: false`): the law is here to
  be read, and no project can be placed in Washington yet. 26 new duty shapes.
  Days are counted under RCW 1.12.040, stated in every caveat that counts them;
  the library holds no Washington holiday calendar.

- **`lang` on an instrument** (contract `instrument` 2.1.0, MINOR: one new
  optional property). The language the instrument's own words are written in,
  as a BCP 47 primary subtag; absent means `en`. French law is read and
  paraphrased in French, not translated into English and back: a duty quoted on
  a French page has to be the French a French contractor reads in the code.
  `scripts/resolve.py` carries it on a concrete's header, so the flattened
  asset says which language each row is in. No obligation rows change.

## v19, 2026-10-18: correction

- **correction** `whs.duty_holders_appoint.gb` (CDM Regulations 2015): the caveat
  now records what reg 5 says about one organisation holding both the principal
  designer and principal contractor appointments. Reg 5(1) names a designer for one
  role and a contractor for the other, reg 2(1) defines 'designer' to include a
  contractor that prepares or modifies a design, and nothing in reg 5 bars one
  organisation from both roles; each appointment meets reg 8's capability test
  for that role. Searched as "can the principal contractor be the principal
  designer" (Search Console, 7-13 Oct 2026, about 40 impressions at positions 68
  to 73, no answer on the page because the row did not say).

## v18, 2026-10-14: no obligation rows change

- **`submission_date` on `variations`** (contract `variations` 1.1.0, MINOR: one
  new optional property). The date an advice was submitted to the client, as
  printed on the form. A variation notice window runs from it: the day a
  document happens to be read is not when the advice was given, and a re-read
  would move it. No obligation rows change.

- **Each release says its kind.** `scripts/release_kind.py --base <previous tag>`
  flattens both trees and classifies every difference: a new instrument, or a
  jurisdiction switched to `supported`, is an addition (called a wave until
  2026-10-20; there is no wave cadence now); a version in force from after
  the tag date is an amendment; a changed field, a removed key, or a version in
  force on or before the tag date is a correction. A new key with no in-force
  date in an instrument that already existed computes as an addition, and its
  section may declare it a correction instead. The release workflow refuses a tag whose
  section does not declare every computed kind, and the obligations asset
  carries `RELEASE.json` (`{tag, kinds, amendments}`; `wave_on` was removed on
  2026-10-20). The first-Monday wave cadence was in force from v18 until then; it
  is not used now: releases are cut when needed. No contract or row changes.

## v17 and earlier

- **MRTS50 carries its quality-system clocks, not only its closeout rows.**
  `obligations/AU-QLD/tmr_mrts50.yaml` gains seven rows read from the March
  2025 edition: the daily lot list (cl 7.4), the one-working-day Hold Point
  release response (cl 8.3.2), the one-working-day Witness Point notice
  (cl 8.3.3), the 14-day testing-frequency nomination (cl 8.5), the per-lot
  Conformance Report (cl 10.1.1), the Nonconformance Report owed within one
  working day of a corrective action request (cl 10.2, the clause's second
  clock) and the four-week handover of the other As Constructed documents
  (cl 12.4.2). Seven duty shapes are added for them, and one event type,
  `practical_completion_reached` on `project_milestone`, for the handover
  watch. No contract changes.

- **Ireland, England, South Africa and Ontario are project countries.**
  `vocab/jurisdictions.json` marks `IE`, `GB`, `ZA` and `CA` `supported: true`,
  switches on `CA-ON`, and adds the subdivisions a project sits in: England
  (`GB-ENG`, `level: state`), Ireland's 26 counties (`IE-CW` to `IE-WW`,
  `level: regional`) and South Africa's 9 provinces (`ZA-EC` to `ZA-WC`,
  `level: state`). Scotland, Wales, Northern Ireland and the other Canadian
  provinces stay absent: the library holds England's Scheme for Construction
  Contracts and Ontario's Construction Act, not theirs. No holiday calendars
  yet: 66 of these countries' 67 windowed rows count days, months or hours;
  South Africa's one working-day row reads unmeasurable until it has a
  calendar. No contract
  or row changes.

- **Library gaps from the 2026-10-06 obligations audit**: every obligation now
  names a register that exists. Prequalification standing reads
  `compliance_prequal`, and the insurance shape's records row reads
  `insurance_certificate` (neither named register existed). The ten approvals
  rows that recorded `not_collected` against a register no contract defines
  (`environmental_authority`, `waterway_barrier_approval`, `vegetation_clearing`,
  `aboriginal_cultural_heritage`), and TfNSW C2's proof of payment, are now
  `record_in_demiton` against `compliance_evidence`: a copy of the approval or
  record, filed against the obligation and accepted by a second person. Two rows
  still name `subcontractor_payment`, which no contract defines: it needs a
  payment-made register fed by a finance system, which is a register to design,
  not a row to re-point. `counterparties` stays empty on purpose (SM031 M6). No
  contract changes.

- **`duty_shape` on every obligation** (contract `obligation` 2.3.0 and
  `platform_obligation` 1.3.0, MINOR: one new optional property each).
  `vocab/duty_shapes.json` names 193 duties, each in a contractor's words, so a
  reader sees one duty from several standards side by side: the latent condition
  notice from AS 2124, AS 4000, AS 4902, GC21, the TMR TIC, MRWA Major Works and
  NZS 3910:2013 is one shape. A row's shape is its key's first two segments,
  except 86 rows that state an existing duty under another key and name that
  duty's shape (NZS 3910's `unforeseen_conditions_notice` is
  `latent_conditions.notice`). 401 base and standalone rows carry it; overrides
  inherit it, and all 440 flattened rows resolve with one: 184 shapes, 77 of
  them stated by two or more instruments. `resolve.tree_errors` refuses a row
  without a shape or with one outside the vocabulary, and `validate.py` refuses a
  shape no row names. The 167 rows added while this was open (SWMS, TfNSW C41,
  Ireland, South Africa, England, Ontario) are shaped too, 57 of them onto a duty
  already named: a notice of project in Ontario, England, Ireland or South Africa
  is `whs.notifiable_work_notice`, England's notified sum and Ireland's default
  due date are `payment.due_date`, and cidb registration is
  `own_commitments.prequalification_standing`.

- **`contract_terms` 1.4.0**: adds `currency`, the ISO 4217 code every amount
  on the record is in. The six money fields (`contract_sum`, `ld_rate`, `ld_cap`,
  `ld_milestones`, `public_liability`, `professional_indemnity`) said `AUD` in
  their unit, so a reader of the record had no currency to carry beside the
  amount and a New Zealand contract had nowhere to say so. Their units now read
  "in `currency`". MINOR: one new optional property. 1.3.2 kept in
  `history/`.

- `contract_terms` 1.3.2 (PATCH): `contract_sum` is ex GST, and its description
  now says so. A letter of acceptance that states the sum "(inclusive of GST)"
  was stored as written, so a consumer reading the sum as the ex GST contract
  value overstated it by the GST. The reader takes the GST out: the document's
  own GST figure when it states one, otherwise the governing country's rate. No
  property, type or requirement changes. 1.3.1 kept in `history/`.

- **Two New Zealand rows corrected** (no row added or removed). NZS 3910:2013
  `latent_conditions.weather_exclusion_rule.nzs3910_2013`: the duty said adverse
  weather is excluded from an extension of time claim, which cl 9.5.1 does not
  say. Cl 9.5.1 excludes weather, and conditions due to weather on the Site,
  from the unforeseen physical conditions claim only; cl 10.3.1 lists inclement
  weather as a ground for an extension of time. The duty and caveat now say so,
  and the caveat's "unless the contractor is away from the Site" becomes the
  clause's "weather away from the Site". HSE Regulations 1995
  `whs.notifiable_work_notice.nz`: consequence `breach` becomes `guidance`.
  Reg 26 states no penalty, and `breach` read as a breach of contract for a
  statutory duty. Both re-read at source on 2026-10-10.

- **Ontario's first obligations** (49 rows, `obligations/CA-ON/`), read on
  2026-10-09 from Ontario e-Laws. `construction_act_1990_on` (32): proper
  invoices and the 7 day deficiency notice, the owner's 14 day notice of
  non-payment and 28 day payment, interest, paying subcontractors in 7 days
  (35 days if the owner has not paid) and the contractor's own notices,
  adjudication (90 day limit, notice, appointment in 4 days, documents in 5,
  determination in 30, payment in 15, leave for judicial review in 35), the 10%
  holdback and its annual and final release, publishing the certificate of
  substantial performance and a notice of termination, preserving a lien in 60
  days and perfecting it in 90, information requests, trust funds and public
  contract bonds. `ohsa_1990_on` (7): critical injury, accident and project
  incident notices, the engineer's opinion and records.
  `construction_projects_regulation_1991_on` (10): registration, the notice of
  project and its posting, trench, suspended platform and tunnel notices, site
  notices, supervisors, emergency procedures and records. New jurisdiction code
  `CA-ON` (`level: state`, `supported: false`). 379 to 428 flattened rows. No
  contract changes.
- **England's first obligations** (36 rows, `obligations/GB/`), read on
  2026-10-09 from legislation.gov.uk's latest revised text.
  `cdm_regulations_2015_gb` (17, S.I. 2015/51, applies in Great Britain):
  client arrangements and pre-construction information, appointing a principal
  designer and principal contractor in writing, notifying the HSE of a
  notifiable project (over 30 working days with more than 20 workers at once,
  or over 500 person days) and displaying the notice on site, the domestic
  client rule, appointee competence, the construction phase plan, preparing
  and handing over the health and safety file, the principal designer's,
  principal contractor's and contractors' duties, worker consultation, written
  demolition arrangements, and the excavation and cofferdam inspection report
  (24 hours) and its retention (3 months). Every CDM row is an `offence`
  through the Health and Safety at Work etc. Act 1974 s 33(1)(c).
  `hgcra_1996_part2_gb` (12, the Construction Act as amended in 2009, applies
  in England, Wales and Scotland): which contracts it governs, stage payments,
  void pay when paid and pay when certified terms, the payment notice within 5
  days of the due date, the payee's default notice, the pay less notice and
  the notified sum, the 7 day suspension notice, and adjudication: notice at
  any time, referral within 7 days, the decision within 28 days, and payment
  of an adjudicated excess within 7 days. `scheme_construction_contracts_1998_eng`
  (7, England's Scheme as amended by S.I. 2011/2333, applying only where the
  contract does not comply): the 28 day period and 7 day due date, the final
  payment 30 days after completion, the 17 day final date, the pay less notice
  7 days before it, the notice of adjudication's content, nominating an
  adjudicator within 5 days, and complying with the decision immediately. No
  vocab or contract changes: `GB` was already a jurisdiction (`supported:
  false`) and the library has no code for England or Great Britain. 343 to
  379 flattened rows.
- **South Africa, first obligations** (34 rows, five standalone instruments
  under `obligations/ZA/`, all read from primary text on 2026-10-09). The
  Construction Regulations, 2014 (19): the construction work permit (r 3(1),
  30 days before work, with the Chief Inspector's Notice 850 of 2018 narrowing
  which work needs one) and starting only once it is issued (r 3(7)), the
  7-day notice of construction work (r 4(1)), the client's specification, the
  principal contractor's and each contractor's health and safety plan and file,
  the file handover, written appointments, Compensation Fund good standing,
  30-day audits and the 7-day audit report, the construction manager and
  health and safety officer, risk assessments and their review, site induction,
  medical fitness, and the client's fatality report. The Occupational Health
  and Safety Act 85 of 1993 (1): leave an incident site undisturbed (s 24(2)).
  The General Administrative Regulations, 2003 (4): the 7-day incident notice,
  the forthwith report, the 3-year record and the 7-day investigation (rr 8,
  9). The CIDB Act 38 of 2000 (3): hold a registration for public sector work
  (s 18), notify changed particulars within 30 days (s 17(1)), renew three
  months before expiry (s 20). The CIDB Regulations, 2004 (7): the annual fee
  and annual confirmation (regs 35(2), 36(2)), the tax clearance certificate
  within three months (reg 36(3)), the grade a tender needs (reg 25), and the
  employer's project registration, status report and dispute notice (regs 18,
  21). No vocab changes: `ZA` was already in `vocab/jurisdictions.json`
  (`supported: false`, unchanged). 309 to 343 flattened rows. No contract
  changes.
- **Ireland's first obligations** (25 rows, `obligations/IE/`), read on
  2026-10-09 from the Irish Statute Book. `construction_contracts_act_2013_ie`
  (14): which contracts the Act governs, the payment claim dates and 30 day
  Schedule default, the payment claim notice within 5 days of the payment claim
  date and its content, the response within 21 days of that date and its
  content, the 30 day due date, the void pay when paid term, the two 7 day
  suspension notices (non-payment, s 5; an unpaid adjudicator's decision, s 7),
  and adjudication: notice of intention at any time, an adjudicator within 5
  days, the referral within 7 days, the decision within 28. The Act states no
  consequence for a missing response, so its row is `guidance`, not
  `liable_full_amount`, and it carries no trigger: its 21 days run from the
  payment claim date, not from when a claim is posted.
  `construction_regulations_2013_ie` (11, S.I. No. 291 of 2013 read with its
  2019 to 2021 amendments): appointing both project supervisors, the client's
  and the construction stage supervisor's notices to the Health and Safety
  Authority, the safety and health plan, the safety file, the safety adviser
  and safety officer headcount duties, Safe Pass and construction skills cards
  and the first-day confirmation, and passing accident notifications to the
  project supervisor. Every regulation row is an `offence` through the Safety,
  Health and Welfare at Work Act 2005 s 77(2)(c). No vocab or contract changes:
  `IE` was already a jurisdiction (`supported: false`). 284 to 309 flattened
  rows.
- **Safe work method statement duties for high risk construction work** (32
  rows). Seven duties added to the model WHS Regulations base, read from Safe
  Work Australia's 5 December 2025 text: prepare the statement before the work
  starts (r 299(1)), do the work in accordance with it and stop work that is not
  (r 300), give the principal contractor a copy (r 301), review it when control
  measures are revised (r 302), keep it until the work is complete (r 303(1),
  (3), (4)) and for 2 years after a notifiable incident (r 303(2), the only row
  with a window), and the principal contractor's duty to obtain it (r 312). All
  four concretes override every one, each re-read against its own text on
  2026-10-09: ACT, NSW (sections), QLD, SA. Local differences live in the
  caveats: the ACT's 19th kind of high risk construction work (crystalline
  silica) and its loose-fill asbestos construction project, Queensland's
  r 299(4) on falls, and South Australia's $450,000 construction project. New
  standalone instrument `ohs_regulations_2017_vic` carries Victoria's own four
  (rr 327(1)(a), 327(1)(b) and (2), 328, 329): it has no copy-to-principal,
  principal contractor or post-incident duty. Every row is `not_collected`
  against `compliance_documents`, which holds a statement but not the work it
  covers. 252 to 284 flattened rows. No contract changes.
- **Payment schedules read from their register**: the eight
  `payment.schedule_due` rows (ACT, NSW, QLD, SA, TAS, VIC, WA, NZ) change
  `evidence.kind` from `not_collected` to `register` (`payment_schedule`, system
  type `finance`). The register exists, and its `claim` field names the claim each
  schedule answers, which `claim_lodged`'s `proof_reference_fields` already pairs
  on. A consumer that skips `not_collected` rows before reading any register can
  now give each claim its own clock (Demiton SM038/X1). No contract changes.
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
