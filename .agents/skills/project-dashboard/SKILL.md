---
name: project-dashboard
description: Build a visual dashboard of a project's real state - features by status, contract and validation evidence, tests and CI, git position, debts and lessons - as a single-file interactive HTML page in the reader's chat language, every number measured from the repository itself (ledger files, git, command outputs), screenshot-inspected before delivery. Use when the user asks for a dashboard, a visual status of the project, a sprint or weekly review, the state of the repo, or at sprint closure. Not for explaining a single result (that is the explainer skill).
---

# Project dashboard

A repository tells its state through scattered files: a feature list, a
contract, a progress sheet, a log, git history. Reading them one by one is
work. A dashboard reads them all and answers one question: where does this
project stand? Every project in the fleet can have this, on demand.

## Data recipe - measure, never invent

1. **Ledger files** - `feature_list.json` (active features and statuses;
   archive count), `contract.md` (criteria), `progress.md` (validated
   evidence per criterion), `log.md` (the ~10 most recent entries). Read
   them from disk; never reconstruct them from memory.
2. **Git** - current branch, ahead/behind versus the remote, the last
   commits (subject and date), count of uncommitted changes.
3. **Health** - the test and lint commands the repository's §7 declares:
   run them when cheap; otherwise cite the last recorded evidence and mark
   it "not re-run". Never present an unexecuted check as green.
4. **Provenance** - every number on the page cites its source file or
   command in a tooltip or caption.

## Page contract

- Single self-contained HTML file: inline CSS and JS, no CDN, no network,
  no build step. Under `scratch/` (or the location the repository
  declares), named `<project>-dashboard-YYYY-MM-DD.html`. Disposable:
  never wired into the docs or the build unless asked.
- Written in the reader's chat language (the language the repository
  declares for replies to the user), whatever the content language is.
- Sections: headline numbers (features by status, checks, git position) -
  feature cards with per-criterion validation state - activity timeline
  from the log - debts and lessons (the §7 pitfalls) - a provenance
  footer with the measurement date and sources.
- Interactivity: filter chips by status, search, hover detail.
- Quality bar: deliberate layout, typography and color hierarchy; a page
  with no styling decisions is not done. Screenshot the rendered page and
  inspect it before delivery - verified means seen.

## Rules

- Read-only on the repository: the dashboard never modifies state files.
- Stale, partial or unverifiable data is labeled as such on the page,
  never silently smoothed over.
- The dashboard accompanies the chat: deliver it with a short summary and
  the one action the picture makes obvious (a blocked feature, a red
  check, a branch never pushed).

## Outputs

- `scratch/<project>-dashboard-YYYY-MM-DD.html` (or the declared location)
- a screenshot kept as evidence of the visual inspection
- a short chat summary, the artifact path, and the next action to take
