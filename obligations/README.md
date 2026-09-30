# The obligation library

One file per **instrument** - an Act, a regulation, a principal's specification,
an award, an approval, a licence - carrying every **obligation** it imposes,
nested under it. A row is cited to the clause that states it. The shape is
[`contracts/instrument.schema.json`](../contracts/instrument.schema.json) and
[`contracts/obligation.schema.json`](../contracts/obligation.schema.json); an
override row is [`contracts/obligation_override.schema.json`](../contracts/obligation_override.schema.json).

## Layout

```
obligations/<JURISDICTION>/<instrument>.yaml          a concrete a project reads
obligations/_model/model-law/<instrument>.yaml        an abstract base: one document adopted verbatim
obligations/_model/shared-shape/<source>/<instrument>.yaml   an abstract base: a duty shape
```

The underscore sorts `_model/` before every jurisdiction and marks it as a kind
of obligation rather than a place. **A base binds no job.** It is never vendored
to a consumer, never run, and never produces an obligation a project reads.

## Three tiers

| Tier | `model_type` | What is shared | What differs per state | Example |
|---|---|---|---|---|
| 1 | `model_law` | the whole obligation, including section numbers | only the act name and the citation | the model WHS Act, adopted by seven states and territories; the model WHS Regulations |
| 2 | `shared_shape` | `duty`, `consequence`, `protection_type`, `disease`, `severity`, `evidence`, `register` | `citation`, `clause`, `window`, `threshold`, `caveat` | environmental approvals, waterway barriers, vegetation clearing, Aboriginal heritage, insurance notification, the construction award, prequalification, certification, competency |
| 3 | none | nothing worth abstracting | everything | the security-of-payment Acts, TMR's MRTS against TfNSW's specs, QBCC licensing against NSW licensing |

A Tier 3 instrument carries no `extends` and stands alone. Make it a Tier 2 base
only when two or more jurisdictions impose the same duty in words that do not
differ; make it a Tier 1 base only when they enacted the same document.

## How inheritance works

A concrete instrument points at its base by **`id`**, never by file path (paths
move; the id is what a `project_obligation` fact already references):

```yaml
# obligations/AU-QLD/whs_act_2011_qld.yaml
id: whs_act_2011_qld
extends: model_whs_act_2011
title: Work Health and Safety Act 2011 (Qld)
publisher: Queensland Parliament
jurisdictions: [AU-QLD]
citation:
  url: https://www.legislation.qld.gov.au/view/whole/html/inforce/2026-08-03/act-2011-018
  access_date: '2026-09-28'
obligations:
- overrides: whs.incident_notice
  key: whs.incident_notice.au-qld
  citation:
    url: https://www.legislation.qld.gov.au/view/whole/html/inforce/2026-08-03/act-2011-018
    clause: s 38(1)-(3)
    access_date: '2026-09-28'
  caveat: '''Immediately'', by the fastest possible means ... Maximum penalty 100 penalty units. ...'
```

`source`, `instrument_type` and `form` come from the base, and so does
`publisher` when the concrete does not state one: an approval-type instrument is
published by the regulator that issues it and inherits the base's publisher,
while a state's Act is published by that state's parliament and states its own.
`id`, `title`, `jurisdictions` and `citation` are the concrete's own. The
concrete's `obligations` are **overrides**, not whole obligations.

Each override names the base obligation it instantiates in **`overrides`**, and
carries the flattened row's own **`key`**. The two differ by design: every
state's keys are jurisdiction-suffixed (`whs.incident_notice.au-qld` against
`whs.incident_notice.au-nsw`), so one base key cannot match two states. The base
key is a handle; the concrete's key is what a project reads.

### What an override may supply

`citation`, `clause`, `window`, `window_source_field`, `threshold`, `grade`,
`basis`, `caveat`. Everything else is inherited.

`duty`, `consequence`, `protection_type`, `disease`, `severity` and `evidence`
are **forbidden** on an override, and `obligation_override.schema.json` refuses
them with `additionalProperties: false`. A state whose duty genuinely differs is
a new obligation under a new `key`, in its own instrument - not an override,
because otherwise the base's disease and evidence mapping would silently drift
from the duty.

### Coverage

- A **`model_law`** concrete must cover every base obligation, with an override
  or with an explicit `removed: true` row. A silent drop is refused: it is the
  failure that reintroduces an unreviewed gap. A `removed: true` row carries no
  `key` and produces no flattened obligation.
- A **`shared_shape`** base is a catalogue, not a floor. A state that does not
  carry a listed duty simply does not override it, and nothing is emitted.

### Grades

`grade` records how close to the primary source the reading was:
`primary_read`, `primary_via_secondary`, `demiton_default` (which must name its
`basis`), and `inherited`.

`inherited` is the honesty guard. It marks a concrete row instantiated from a
base without re-reading that jurisdiction's own text, so the register never
claims it verified a clause it inherited. A base authored from a document family
rather than a clause-by-clause reading carries **no** `grade` on that duty, and
the concrete that first reads the state's text must supply one.

## Checks

`scripts/validate.py` runs every check a JSON Schema cannot, because it needs
more than one document:

- an instrument `id` is unique (`extends` resolves by id, so a duplicate is
  ambiguous);
- `extends` names an instrument in this tree, and that instrument is `abstract`;
- no cycle in `extends`;
- an override names an obligation its base actually carries;
- a `model_law` concrete does not silently drop a base obligation;
- every resolved row has a `grade`;
- a concrete names a jurisdiction, and an abstract base names none;
- `model_type` appears on an abstract base and on nothing else.

`scripts/resolve.py` is what flattens the tree to the set a project reads:

```
python3 scripts/resolve.py --count      # obligations across every concrete
python3 scripts/resolve.py --flatten    # the resolved instruments, as JSON
python3 scripts/resolve.py --out DIR    # one flattened YAML per concrete instrument
```

`validate.py` imports the tree checks from `resolve.py`, so the checks a tree
must pass and the flattening it produces cannot drift apart.

## Adding an instrument

1. Check the three-tier table. If two or more jurisdictions share the duty in
   the same words, author a base under `obligations/_model/` and make the
   concrete an override. Otherwise stand it alone.
2. Cite the clause, with an access date, from the primary source. A row with no
   citation is refused by the schema before a person sees it.
3. Give every concrete row a `grade`. If you instantiated it from a base without
   re-reading the state's text, say `inherited` rather than `primary_read`.
4. Run `python3 scripts/validate.py` and `python3 -m pytest tests/ -q`.
