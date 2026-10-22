# Contributing

You don't need to ask first. Open a pull request against one contract.

## The shape of a pull request

**One register per pull request**, so each can be reviewed and merged on its own.

1. **Edit `contracts/<shelf_type>.schema.json`** (or `research/<name>.schema.json`
   for a disease-economics register). Add a field, widen an enum, tighten a
   description - whatever the change is.
2. **Bump `x-schema-version` or `x-demiton-contract-version`** (whichever the
   file already carries) by at least as much as [METHOD.md](METHOD.md) Section 3
   requires for what you changed. CI tells you if it isn't enough.
3. **Run the checks**, or let CI run them:

   ```
   uv sync
   uv run python scripts/validate.py
   uv run python scripts/bump_check.py --base origin/main
   uv run python scripts/leak_check.py
   ```
4. **Say why**, in the pull request description: what the field is for, and
   where you'd expect it to come from.

## Which branch: `main`

All obligation changes go to `main`. A release is cut and deployed when needed;
there is no separate branch or date for additions.

| The change | Kind |
|---|---|
| a new instrument, a new edition of a contract form, a new duty the library did not carry, a jurisdiction switched to `supported` | addition |
| a rule an amending law changes from a date after the release (a new version with `in_force.from`, or a repeal with `in_force.until`) | amendment |
| a row that was wrong: a field fixed, a key removed | correction |

A pull request's CI prints the kinds it computes; the release tag's CHANGELOG
section must declare them. A new duty that the library should always have carried
is a correction: say so in the pull request.

## Cutting a release

Cutting a tag turns `## Unreleased` in `CHANGELOG.md` into `## vN, YYYY-MM-DD: <kinds>`.
The date is the tag date: the release workflow classifies the diff against it, and
refuses the tag when it is not the day of the tag commit in Australia/Brisbane (a
runner's UTC clock is a day behind Brisbane for ten hours of every day, so a clock is
never the date). Commit the section, then tag that commit.

`RELEASE.json`, attached in `registers-obligations-vN.tar.gz`, is
`{tag, kinds, amendments: [{key, from}], warnings: [str]}`. `warnings` holds one line for
each amendment that starts fewer than 20 business days after the tag date (SM052
decision 16), and is `[]` when there are none. The same lines appear as a `::warning::`
annotation on the release run and under "Late amendments" in the GitHub release notes.
It is a warning, never a refusal.

## Proposing a new register

Open an issue with the [register proposal template](../../issues/new?template=propose-register.yml)
first, or go straight to a pull request adding `contracts/<name>.schema.json` if
you already know its shape. Either way, say what it's for and what would fill it.

## What gets rejected, and why

- **A version bump that's too small for the change.** CI computes the bump a
  change actually needs; it does not trust a contributor's own label.
- **Anything naming a real organisation, or reading like an internal
  implementation note.** This repository publishes the *shape* of a register,
  never what a tenant's own data looks like or why a field was built. CI's leak
  check catches known patterns; a human reviewer catches the rest.
- **Deleting a register or a version.** Deprecate it instead, with a reason.

## Disputing a contract

Open a [dispute issue](../../issues/new?template=dispute.yml), or a pull request
that changes the file directly. [GOVERNANCE.md](GOVERNANCE.md) says who decides
and how fast.

## Conduct

Be direct and be kind. Disagree with a contract, not with the person who wrote it.
