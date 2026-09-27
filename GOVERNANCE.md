# Governance

## Who decides

**Demiton maintains this repository and merges every change. Demiton is one person today.**
These are the shapes Demiton's own product reads and writes, so Demiton has a
direct interest in what they look like. We would rather you read that here than
discover it.

## What Demiton will not publish here, and why

A register's contract - its fields, their types, which are required - is
published in full. What produced that contract is not: the evidence for why a
field exists, which internal proposal designed it, which system first supplied
it, and (most importantly) anything describing a real tenant's own data. A
pull request that would introduce any of that is refused, whether or not CI's
own leak check catches it first.

This is a narrower promise than disease-economics' evidence trail: a register's
*shape* is open to public review and change; what a specific organisation has
recorded in that shape never is.

**The `obligations/` tree (SM030) is the one exception to "shapes only", and
its own line, not a widening of the one above:** what it publishes is
**public instruments, not recorded data** - an Act's clause, a specification's
requirement, an award's rate, cited to its source. Never a tenant's contract,
amendment, or which of these a tenant switched on. A `project_obligation` fact
recording that a specific organisation switched on a specific obligation for a
specific job never leaves Demiton's own systems, public or private.

## Who reviews an obligation

**Justin reviews every pull request against `obligations/` before merge, with
no exception for an addition that only adds.** An obligation row is a
liability surface (a wrong window is wrong for every customer who reads it):
GOVERNANCE already says Demiton is one person, and this is the pull request
where that one person's judgment cannot be skipped by CI going green. A
proposal opened by Demiton's own product on a customer's behalf (an org admin
proposing a public obligation their job needs) is reviewed the same way as one
opened by anyone else.

## How fast

A first response to every dispute issue and pull request within **10 working days**.

## How a change is decided

1. You open a pull request against a contract, or a dispute issue.
2. If the change only adds - a new optional field, a widened enum - it is
   usually a fast merge once CI's version-bump and leak checks pass.
3. A change that could break existing data (MAJOR, per [METHOD.md](METHOD.md)
   Section 3) gets a slower review, because Demiton has to check it against
   what the field is actually used for internally before merging.
4. One of three outcomes, each with its reasoning written in the pull request:
   - **Merged** - the contract's new version is released.
   - **Rejected** - the contract stands, with the reason recorded.
   - **Deferred** - a real gap, not yet resolved either way.

## Appeals

**There is no appeal at present.** We would rather say so than promise a second
reviewer who does not exist.

## Floods

If the repository is flooded with pull requests or issues that carry no
rationale, we will use GitHub's interaction limits to restrict new
contributions to prior contributors for a period, and say so here while it applies.
