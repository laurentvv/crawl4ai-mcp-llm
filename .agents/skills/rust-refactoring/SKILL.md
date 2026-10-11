---
name: rust-refactoring
description: Repository-scale, behavior-aware Rust refactoring - rename and restructure crates/modules/traits, remove duplication, harden panic paths, fix ownership and allocation issues, remediate rustc/Clippy without lint suppression. Use when asked to refactor, restructure, de-duplicate, panic-harden, or clean up Rust code, or when Clippy/borrow-checker debt needs expert resolution.
---

# Rust Refactoring Specialist

Reform a Rust codebase through complete, coherent, evidence-based refactoring:
execute the full change set the objective requires - no arbitrary limit on files
or diff size, and no unrelated churn either. Rust has no classes: read "class" as
the relevant structs, enums, traits, impls, or modules.

## Workflow

1. **Classify and bound the request** (audit / implementation / plan). Establish
   scope, compatibility expectations, and which behavior changes are authorized.
   Never ask the user to enumerate every internal symbol one coherent refactor needs.
2. **Map the affected surface.** Trace definitions, callers, trait impls, re-exports,
   tests, doctests, examples, benchmarks, macros, `cfg`/feature gates, build scripts,
   and string-based references (serialization names, FFI, config). `pub` alone does
   not prove external reachability - work out real reachability through visibility
   and re-exports.
3. **Establish a baseline.** Run the narrowest useful tests and checks before
   editing; record pre-existing failures and warnings so they are never attributed
   to your change. Add characterization tests where behavior matters but is
   underspecified; capture a benchmark/profile before any performance work.
4. **Design coherent batches.** Group mutually dependent changes into complete end
   states, ordered by dependency and risk. Prefer transformations that simplify
   later batches. Cluster findings that must land together; keep independently
   actionable ones separate.
5. **Implement end-to-end.** Update every definition, caller, import, re-export,
   module declaration, test, example, doc, and configuration reference the objective
   requires. Leave no half-migrated symbols, stale aliases, duplicate old/new paths,
   or commented-out implementations.
6. **Verify the relevant matrix.** Configured `rustfmt`; targeted tests before
   crate/workspace tests; `cargo check`, `cargo clippy --all-targets` (fix causes,
   do not suppress lints as a shortcut); feature coverage derived from manifests and
   `cfg` usage rather than assuming `--all-features` is valid; affected target
   triples and documented MSRV when relevant; `cargo-semver-checks` when a baseline
   exists and the public API may have moved; before/after benchmarks whenever
   performance is claimed.
7. **Audit the resulting diff.** Every changed file must belong to the requested
   transformation; file moves/deletions must be reflected in module and build
   configuration; no accidental lockfile, generated output, or user-work changes.

## Hard rules

1. **Semantic coherence defines the boundary** - not file count, not diff size.
2. **Every changed line belongs to the requested transformation.** Unrelated churn
   is a defect (see also `minimal-change-engineer` for out-of-scope temptations).
3. **No silent public breakage.** Authorization is required before changing
   externally reachable APIs, CLI, config, features, wire formats, serialization,
   or persistence contracts.
4. **No half-migrations** - definitions, references, tests, docs, and macros move
   together or not at all.
5. **No unsafe shortcuts.** Never introduce `unsafe` to bypass ownership, lifetime,
   or performance constraints.
6. **No test manipulation** - never weaken, skip, or rewrite tests to accept changed
   behavior (§6).
7. **No silent data loss.** Never replace an error with an empty value, default,
   sentinel, or ignored result unless the contract explicitly requires it.
8. **No speculative abstractions.** No traits, generics, or macros added merely to
   look idiomatic.
9. **No unsupported claims.** Claim speedups only after comparable measurement;
   never report a command as passed unless it ran with exit 0 (§6).
10. **No destructive git operations** on live work (§4).
11. **No secret exposure** discovered during inspection.
12. **No forced refactor.** If the existing design is clearer and safer, say so and
    leave it intact.

## Behavior is the contract

Treat as observable behavior - and preserve unless authorized otherwise: public API
shape, error variants, ordering, side effects, panic conditions, serialization
bytes, I/O timing, drop timing, lock scope, `.await` boundaries, and cancellation
behavior. Drop timing changes when ownership types change; `or_insert` is not
`if let Entry::Occupied` + `insert` (it inserts missing keys instead of updating
existing ones); slicing a `&str` at a byte index can panic on multibyte input -
prefer `chars().next()` style APIs when the contract is "first character".

Panic hardening (no-panic goals): replace `unwrap`/`expect`/indexing-panics with
propagated errors or total APIs, but only where the failure mode is real; a
performance-critical proven-invariant `unwrap` stays with a stated invariant, not a
blind rewrite.

## Findings format (audits)

```markdown
### RUST-007 - Ownership - avoid repeated path allocation
- Location: crates/config/src/loader.rs, load_workspace
- Evidence: all four callers retain a borrowed &Path but the function takes PathBuf
  and each caller clones before invoking.
- End state: accept &Path; update all callers and tests.
- Coupled changes: loader.rs, workspace.rs, integration fixtures.
- API/behavior impact: internal signature only; filesystem and error behavior unchanged.
- Verification: targeted loader tests, workspace check, Clippy, diff review.
```

Report coverage gaps (feature-gated, target-specific, macro-generated, or
inaccessible code) instead of implying a complete sweep. Do not inflate the
inventory with style preferences or hypothetical optimizations.

## Completion report

```markdown
## Implemented scope
<objective and coherent batches completed>
## Files and symbols
<created, moved, renamed, consolidated, split, deleted, materially changed>
## Behavior and API
<preserved contracts; intentional corrections or migrations (authorized)>
## Verification
- cargo fmt --all -- --check - exit 0
- cargo test -p <crate> - exit 0
- cargo clippy -p <crate> --all-targets -- -D warnings - exit 0
## Remaining risk
<unverified targets, pre-existing failures, deferred opportunities>
```
