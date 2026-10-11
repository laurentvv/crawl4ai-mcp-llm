# NOTICE — provenance and local modifications

- **Upstream**: [kajisho5/ffmpeg-skill](https://github.com/kajisho5/ffmpeg-skill)
- **Version vendored**: v2.7.0, commit `cb10cfbc5373a89feef0fda8c4d1c92e035bbe36` (2026-10-09)
- **License**: MIT, unchanged in `LICENSE`. Upstream remains the author of record for everything not listed below.
- **Vendored**: into `generator-assets/.agents/skills/ffmpeg-skill/` on 2026-10-09, at the user's request ("grab the skill and tweak it to your liking"), then promoted to the agents-kit fleet copy (see Fleet distribution below).

## Vendored subset

`SKILL.md`, `scripts/` (42 tools + `_common/` + `_contract.py` + `_platforms.py`), `references/` (5 files), `templates/`, `LICENSE`.

## Not vendored

`mcp/` (MCP stdio server), `bin/` + `package.json` (npx installer), `tests/`, `evals/`, `demos/`, `examples/`, `docs/` (12 MB rendered docs), `assets/`, `.github/`, `.claude*/`, upstream `AGENTS.md`/`README.md`/`CHANGELOG.md`/`CONTRIBUTING.md`/`SECURITY.md`/`CODE_OF_CONDUCT.md`, `.gitignore`/`.npmignore`.

## Local modifications (keep minimal; re-check on every upstream re-sync)

1. `SKILL.md` — added the "Fleet adaptation (agents-kit distribution) — read first" block: Windows 11/Git Bash (`python`, no `python3`), ffmpeg at `C:\ffmpeg` + `C:\ffmpeg\README.md` duty, measured machine gaps (no vidstab filters, font coverage, no local parakeet, CPU x264/x265 only — `--hw` is Apple-only), a rule that repo-specific overrides (heavy-generation gates, per-project loudness specs, output locations) live in the HOST repo's AGENTS.md §7, knowledge-sync duty, not-vendored list. Reworded the two `python3`/`npx` invocations (workflow step 0, intro paragraph) to `python`; MCP sentence replaced by a not-vendored pointer. (Fleet-generalized 2026-10-09: replaced the original generator-assets-pinned adaptation block; its specifics remain recorded in generator-assets AGENTS.md §7.)
2. `references/gotchas.md` — one `python3` → `python` (doctor invocation).
3. `references/scripts.md` — "MCP server" section replaced by a NOT-vendored note.
4. `package.json` — new minimal manifest (`2.7.0+gas.1`): only feeds `scripts/_contract.py` `skill_version()` so `doctor` reports a truthful version for this copy instead of "unknown".
5. This `NOTICE.md` — new file.

No `.py` script was modified. Upstream is already Windows-hardened (fontconfig fallback via `C:\Windows\Fonts`, concat-demuxer instead of `-pattern_type glob`, crash exit-code handling — see its `references/ci-platform-pitfalls.md`).

## Fleet distribution (agents-kit)

- Promoted to the agents-kit fleet on 2026-10-09 (`skills author`, source "(authored)"): the kit copy in `skills/ffmpeg-skill/` is the single distribution source, deployed to the repositories' `.agents/skills/ffmpeg-skill/` as byte-identical copies under a fingerprint lock. "(authored)" means no upstream wiring: `skills update` never re-imports upstream over this fork — the re-sync recipe below stays a manual, reviewed step.
- Distributed fleet-wide via agents-kit 2026-10-09: installed in generator-assets, ai-doc2video, video-analys-ia.
- This NOTICE.md is the fork's provenance marker: the kit's repository guard exempts skill folders carrying it from the English-only scan, because the vendored upstream files are external content (their multilingual caption/filler data included) distributed byte-identical.

## Upstream re-sync recipe

```bash
git clone --depth 1 https://github.com/kajisho5/ffmpeg-skill /tmp/ffmpeg-skill-upstream
# copy scripts/ references/ templates/ LICENSE SKILL.md over this directory,
# then re-apply the 4 modifications above (this file lists them exhaustively)
```
