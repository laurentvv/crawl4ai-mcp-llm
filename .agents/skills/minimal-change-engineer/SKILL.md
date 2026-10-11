---
name: minimal-change-engineer
description: Produce the smallest diff that solves the stated problem and refuse scope creep. Use when fixing a bug, implementing a small feature or config change, reviewing a diff that grew beyond its task, or whenever you feel a "while I'm here" impulse. Prevents bug-fix PRs from becoming refactor avalanches.
---

# Minimal Change Engineer

Do exactly what the task asks, and nothing more. The value of this skill is measured
in lines not written: most over-production (by engineers and by AI tools alike) is
where regressions, review fatigue, and scope creep come from.

## Workflow

1. **Read the task literally.** The verbs define the scope: "fix" means fix, not
   improve; "add a button" means add a button, not redesign the form. If the task
   looks like three tasks in a trench coat, propose splitting it - do not silently
   do the bigger interpretation.
2. **Find the minimum surface.** Trace the smallest set of files and functions that
   must change for the task to succeed. If you find yourself opening a fourth file,
   stop and ask whether it is strictly necessary.
3. **Write the smallest diff that works.** Prefer the boring, obvious change over
   the elegant one; when two approaches both work, take the one with fewer changed
   lines.
4. **Walk the diff line by line** before submitting and ask of every changed line:
   "does the task require this exact line?" If the answer is "no, but it would be
   nicer", delete it.
5. **List the follow-ups you did NOT do** in the delivery message ("follow-ups noted
   but not done"): that is where "while I'm here" temptations go - captured, never
   executed silently.
6. **Resist review-time expansion.** When asked "while you're here, can you also
   ...", decline for this diff and open/queue a follow-up. Expansion at review time
   is how clean PRs become messy ones.

## Hard rules

1. **Touch only what the task requires.** A file not mentioned by the task and not
   strictly required to make it work stays unopened.
2. **Three similar lines beat a premature abstraction.** Extract a helper at the
   fourth occurrence, not before.
3. **No defensive code for impossible cases.** Trust internal invariants and
   framework guarantees; validate only at system boundaries (user input, external
   APIs, files).
4. **No improvements disguised as fixes.** A bug-fix commit contains only the bug
   fix; refactors get their own branch, PR, and contract.
5. **No compatibility shims for unused code.** If something is genuinely dead,
   delete it cleanly - no `// removed` comments, no `_old` aliases.
6. **No speculative generality.** No config flags, strategy patterns, or hooks for
   future callers that do not exist. If a third mode ever shows up, extract then.
7. **No test manipulation.** Never weaken or skip a test so the smaller diff looks
   green (§6).

## Scope self-check (run before delivering)

```markdown
## Scope self-check
Task as stated: <exact task text>
Files touched:
- <file> - required because: <reason>
Lines I was tempted to add but did not (follow-ups instead):
- <the "while I'm here" items>
Hypothetical cases I am NOT defending against:
- <cases that cannot actually happen>
Abstractions considered and rejected (occurrences < 4):
- <helpers left as duplicated lines>
Diff size: <X added, Y removed> - could it be smaller? <yes: make it smaller / no: why>
```

## Scope-creep traps (recognize them by name)

- **"While I'm here"** - the most common form of unrequested change.
- **"For future flexibility"** - abstractions for callers that never arrive.
- **"Defensive coding"** - try/except for things that cannot throw.
- **"Modernization"** - rewriting working code in a newer style.
- **"Consistency"** - touching unrelated files because "everything else uses X".
- **"Cleanup"** - removing things you assume are dead without proving it.

For "is this code dead?": the minimal proof is to delete it and run the tests -
either it is needed (revert) or it is not (commit). Never a deprecation comment as
a half-answer.

## Calibration

- A single-task diff over ~30 changed lines deserves a justification; a bug fix
  touching more than 2 files usually means scope leaked in.
- Small diffs review in minutes, have small blast radius, and revert cleanly.
  When in doubt, shrink it.
