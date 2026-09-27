# Method

How a register's contract gets here, and the rules every contract is held to.
CI enforces every rule a machine can check (`scripts/validate.py`,
`scripts/bump_check.py`, `scripts/leak_check.py`).

## 1. What a contract is

One JSON file per register: its fields, their types, which are required, and
what each one means. Two shapes live side by side here, because they came from
two different places before this repository existed:

- **`research/`** is strict draft 2020-12 JSON Schema. Its registers - finding,
  source, protection, and eventually organisation - describe the disease-economics
  evidence record, and their version key is `x-schema-version`.
- **`contracts/`** and **`history/`** are JSON-Schema-*shaped*: the same
  `properties`/`required`/`type` structure, but `type` is drawn from Demiton's
  own closed field-type vocabulary (`decimal`, `money`, `currency`, `date`,
  `datetime`, `jurisdiction`, alongside the standard JSON Schema primitives),
  not the JSON Schema spec's own `type` enum. Their version key is
  `x-demiton-contract-version`. Unifying the two version keys is a known,
  undecided follow-up - see the repository's issues.

## 2. Public and private

Every contract here is the *public* half of a register definition. What stays
private, in Demiton's own systems:

- **why a field exists**: the evidence, the internal proposal, which system
  first supplied it, a vendor's own field name for it.
- **a tenant's own data**: nothing here describes what any organisation has
  actually recorded, only the shape a record of that kind takes.

A field, an axis or a measure entry carries only the keys this repository's own
export allows through; a key nobody has named yet stays private by default.

## 3. Versioning

Every contract carries a full semantic version. CI computes the required bump
from what actually changed - not from what a contributor claims - by walking
the schema's properties, required lists, enums and types:

| Bump | When |
|---|---|
| MAJOR | a property removed, a new requirement, an enum narrowed, a type changed |
| MINOR | a property added, an enum widened |
| PATCH | anything else (a description, a pattern's wording, an example) |

A required list inside a property that did not exist in the old version is not
a new requirement on old data - the whole property is new, and only optional
unless the *parent* schema now requires it too.

## 4. A register is never deleted

Only deprecated, with a reason recorded in its history. A version once released
never changes; a correction is a new version with its own entry in
[CHANGELOG.md](CHANGELOG.md).

## 5. Disputing or proposing a change

See [CONTRIBUTING.md](CONTRIBUTING.md) for the shape of a pull request, and
[GOVERNANCE.md](GOVERNANCE.md) for who decides and how fast.

## 6. The obligation library (SM030)

A third shape lives here besides `research/` and `contracts/`/`history/`:
`obligations/<jurisdiction>/*.yaml`, one YAML file per **instrument** - an Act,
a principal's specification, an award, a licence - carrying every
**obligation** it imposes nested under it. Checked strictly, with the real
`Draft202012Validator`, against [`contracts/instrument.schema.json`](contracts/instrument.schema.json)
and [`contracts/obligation.schema.json`](contracts/obligation.schema.json):
unlike the shelf-derived contracts, these describe data this repository is
itself the source of record for, so there is no reason to relax the check to
the closed field-type vocabulary those came with.

Two checks a JSON Schema `enum` cannot express, because the valid set lives in
a sibling file, run alongside it: an instrument's `instrument_type` must be a
member of `vocab/instrument_types.json` keyed by its own `source`, and every
jurisdiction code (an instrument's `jurisdictions`, an obligation's own, if it
narrows further) must be a member of `vocab/jurisdictions.json`. `scripts/validate.py`
runs both.

Every obligation carries its own `citation` (URL, clause, access date) -
required by the schema, so a row transcribed with no primary source is refused
before a person looks at it, not caught in review. [GOVERNANCE.md](GOVERNANCE.md)
"Who reviews an obligation" is the human control for everything a schema
cannot check (whether the citation actually says what the row claims).
