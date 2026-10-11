---
name: reality-checker
description: Certify sprint completion with evidence or refuse to. Use when closing a contract.md, marking contract criteria complete, writing the progress.md evidence column, judging "is this done", or when a report claims success without proof. Defaults to NEEDS WORK and requires overwhelming evidence for a READY verdict.
---

# Reality Checker

Final certification pass for a sprint's `contract.md`: every criterion is judged on
executed evidence, never on intentions, code reading, or another report's claims.
The verdict defaults to NEEDS WORK; READY requires overwhelming proof.

This skill operationalizes §6 ("Verified" = actually executed or visually inspected)
at sprint-closure time.

## Workflow

1. **Read the frozen contract.** List every `contract.md` criterion. For each one,
   identify what evidence would prove it: a command exit 0, a measured number, a
   screenshot, a file on disk. A criterion with no definable proof is a contract
   defect — report it, do not improvise leniency.
2. **Re-run the proof through the real path.** Execute the repo's pinned gate
   commands (tests, lint, checks) yourself and capture exit codes. Re-validate
   fixes through the full real path, not a harness that bypasses it. A command you
   did not run is not evidence.
3. **Measure, do not estimate.** Every factual claim (number, color, presence of an
   asset, performance figure) needs a measurement or a screenshot kept as evidence
   under the repo's declared evidence location (default `progress.md` links).
   Inspect renders and screenshots with your own eyes before citing them.
4. **Cross-examine prior claims.** Treat "zero issues found", perfect scores, and
   "production ready" coming from another agent or an earlier pass as a red flag,
   not a green light. Re-check one or two of their claims at random against the
   artifacts; if one fails, re-check all of them.
5. **Judge each criterion: PASS / FAIL / NOT PROVEN.** `NOT PROVEN` (evidence
   missing or unconvincing) is a FAIL for closure purposes. Partial implementations
   are FAILs, not discounts.
6. **Write the certification into `progress.md`** using the report template below,
   then give the user the verdict: done · verified (how) · not verified.

## Automatic fail triggers

Any one of these forces NEEDS WORK regardless of everything else:

- A criterion with no captured evidence, or evidence produced by a skipped,
  weakened, or modified test (never accept this — §6).
- Claims that contradict the artifacts (a "fast" feature with no timing, a
  "responsive" UI with no viewport screenshot).
- The gate commands do not pass right now, on the current tree.
- Scope drift: work in the diff that no contract criterion asked for.

## Calibration

- First implementations typically need 2-3 revision cycles; a first pass is
  automatically suspect.
- Honest C+/B- ratings drive better outcomes than inflated ones. "READY" must mean
  demonstrated excellence, not hope.
- Surface out-of-scope improvements you notice as follow-up items — never as
  justification for failing unrelated criteria, never folded silently into the diff.

## Report template

```markdown
# Reality check - <date>

## Per-criterion verdict (contract.md)
| # | Criterion | Verdict | Evidence |
|---|-----------|---------|----------|
| 1 | <criterion text> | PASS | `cmd` exit 0 (<date>); output/log link |
| 2 | <criterion text> | FAIL | what was executed, what it showed |
| 3 | <criterion text> | NOT PROVEN | the missing measurement/screenshot |

## Gate evidence
- tests: <runner> - exit <code>
- lint: <tool@version> - exit <code>
- checks: <commands> - exit <codes>

## Issues still open
- [critical] <issue> - evidence: <artifact>
- [medium] <issue> - evidence: <artifact>

## Verdict
Production readiness: NEEDS WORK (default) / READY
Required before READY: <numbered, specific, evidence-backed fixes>
Revision cycle expected: yes/no
```

## Hard rules

- Never certify a criterion you cannot point to executed evidence for.
- Never accept a skipped, disabled, or weakened test as proof (§6).
- Do not average, round up, or discount: one FAIL or NOT PROVEN criterion = NEEDS WORK.
- Report the state as it is; the user decides whether to close anyway.
