# registers

Every register Demiton reads and writes - what a project, a worker, a variation
or a piece of plant looks like as data - as one versioned, public JSON Schema
contract per register.

**Browse them at [docs.demiton.io/concepts/register-catalog](https://docs.demiton.io/concepts/register-catalog)**,
built from this repository. The [research registers](research/) also power
[research.demiton.io](https://research.demiton.io)'s Schemas and history tab.

## What is here

- **[`contracts/`](contracts)** - the current public contract for every tenant and platform
  register: 172 today, one file each. Each carries a semantic version.
- **[`history/`](history)** - every past version of every register in `contracts/`, so a
  reader (or a piece of code) can see exactly what a field meant at a given point in time.
- **[`research/`](research)** - the four registers behind
  [disease-economics](https://github.com/demitonapp/disease-economics): what a
  published figure, its source and its publisher look like as data.
- **[`vocab/`](vocab)** - shared vocabularies more than one register's fields draw on.
- **`obligations/`** - the public obligation library (SM030): one file per instrument - an Act, a
  principal's specification, an award, a licence - carrying every duty it imposes, cited to its clause.
  What a civil job in Demiton is protected against comes from here, not the other way round. Shape:
  [`contracts/instrument.schema.json`](contracts/instrument.schema.json) and
  [`contracts/obligation.schema.json`](contracts/obligation.schema.json). Populated by SM030 O2.

## What is deliberately not here

A register's *contract* - its shape - is public. What a specific tenant's data
looks like inside that shape is not, and neither is the evidence trail behind a
field's design (why it exists, which system it came from, which internal file
first proposed it). That stays in Demiton's own systems. See
[GOVERNANCE.md](GOVERNANCE.md) for exactly where that line sits and why.

## Versioning

Every contract carries a full semantic version (MAJOR.MINOR.PATCH):

- **MAJOR** - a field removed, a new requirement, an enum narrowed, a type changed:
  existing data may stop validating.
- **MINOR** - a field added, an enum widened: existing data still validates.
- **PATCH** - anything else: a description, a pattern's wording, an example.

CI (`scripts/bump_check.py`) refuses a pull request whose version bump is smaller
than the change it makes. [`CHANGELOG.md`](CHANGELOG.md) lists what changed in
each release.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). One register per pull request. CI checks
that the document is valid, that the version bump is large enough, and that
nothing tenant-specific or internal has leaked in.

## Licence

The contracts are [CC BY 4.0](LICENSE): reuse them freely, with attribution
("registers by Demiton"). The scripts are [MIT](LICENSE-CODE).
