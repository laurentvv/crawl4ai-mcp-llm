---
name: agy
description: Generate and iterate images with Google Antigravity's agy CLI in headless mode, and script non-interactive agent runs with machine-readable output. Use whenever the user asks for a generated or edited image (illustration, texture, icon, concept art, variation), mentions agy or Antigravity, or wants an agent run from a script, a batch or CI.
---

# agy - headless Antigravity CLI

`agy` (Google Antigravity) runs an agent non-interactively: one prompt in
(`-p`), the response on `stdout`, diagnostics on `stderr`, process exits. It
reuses the logged-in account's cached credentials - authenticate once with an
interactive `agy` session before any headless use.

Everything below was verified live on agy 1.2.16 (Windows 11, Git Bash),
2026-10-04. Official reference: https://antigravity.google/docs/cli/headless/

## Generate an image (the core recipe)

Image generation is an agent TOOL (`generate_image`, delegated to an
image-generator subagent), not a model slug: `agy models` lists text models
only, any of them can drive the generation. The image bytes are produced
server-side; the agent then copies the file into the working directory with a
shell command - and that copy is the whole permission problem.

1. Work from a disposable directory (`scratch/...`, a temp dir): the run
   needs `--dangerously-skip-permissions` (see below), so give it nothing
   valuable to touch.
2. One image, one command:

```bash
mkdir -p scratch/agy-images && cd scratch/agy-images
agy -p "Generate an image: <subject, color/material, background, lighting, framing>. Save it as <name>.png in the current directory." \
    --dangerously-skip-permissions --output-format json
```

3. Verify THREE things before claiming success - a denied run still exits 0
   with status SUCCESS:
   - the envelope has `.status == "SUCCESS"` AND `denied_actions` absent or
     empty,
   - the file exists on disk with the right magic bytes (PNG / JPEG),
   - the image was actually LOOKED at (open it, screenshot it, vision pass):
     verified means seen.

```bash
uv run --no-project python -c "import pathlib; b=pathlib.Path('<name>.png').read_bytes()[:8]; print('PNG' if b.startswith(b'\x89PNG\r\n\x1a\n') else b)"
```

## Why --dangerously-skip-permissions

- The final file copy runs through `run_command`; in headless mode an
  unapproved command is SOFT-DENIED: the run "succeeds" (exit 0, status
  SUCCESS, empty or partial response) and the envelope carries
  `denied_actions` - the image never lands in the working directory.
- Telling the agent to "use cp" does NOT reliably hit an existing
  `permissions.allow` rule - verified twice, denied both times.
- `write_to_file` cannot carry binary image data (observed: junk test
  files, then a denial).

So keep the flag and contain the blast radius: disposable cwd, a prompt you
wrote, nothing sensitive in reach. Scoped `permissions.allow` rules are the
alternative when a run must work without the flag.

## Salvage a denied run

The generation itself usually completed before the denied copy. The raw image
waits under the CLI's brain directory, named after the prompt with a
timestamp - and the extension can drift (a `.png` request landed as `.jpg`):

```
~/.gemini/antigravity-cli/brain/<conversation_id>/<prompt_name>_<timestamp>.jpg
```

Take `conversation_id` from the envelope, copy the newest file out, rename it.

## Iterate on an image

Conversations continue headless: `-c` continues the most recent one,
`--conversation <id>` a specific one. Reference-based edits (recolor,
restyle, variation) work, reading the earlier image from the conversation
context; expect roughly double the cost and duration of a fresh generation.

```bash
agy -c -p "Same subject, <change only>. Save it as <new-name>.png in the current directory." \
    --dangerously-skip-permissions --output-format json
```

## Machine-readable output

- `--output-format text` (default): the response text only.
- `--output-format json`: one envelope at the end - `conversation_id`,
  `status`, `response`, `error`, `duration_seconds`, `num_turns`, `usage`
  (token counts) and `denied_actions` (undocumented in the official page,
  present in 1.2.16).
- `--output-format stream-json`: NDJSON events (`init`, then `step_update`
  with tool calls, then one `result`) - the way to see WHICH tools ran.

Do not assume `jq` is installed - parse with Python:

```bash
agy -p "..." --output-format json | uv run --no-project python -c "import json,sys; e=json.load(sys.stdin); print(e['status'], e['response'])"
```

`--json-schema` constrains the answer to a schema; `--model <slug>` pins a
model and fails loudly (exit 1) on an unknown slug; `--effort
low|medium|high` trades depth for speed (1.2.16 also accepts `xhigh|max`).

## Expectations and pitfalls (measured 2026-10-04, agy 1.2.16)

- One image: 45-100 s and 45k-80k tokens; one reference edit: ~200 s and up
  to 166k cumulative tokens. Budget before batching.
- The local binary can drift from the docs: 1.2.16 waits indefinitely by
  default (`--print-timeout 0s`; the docs describe a 5 m ceiling) - set the
  flag explicitly in scripts, and re-read `agy --help` on the target
  machine before trusting memorized flags.
- The enclosing repository leaks into the run: agy reads the workspace
  AGENTS.md and `.agents/skills/` of the cwd's repo (observed: replies in
  the repo's chat language, workspace skills auto-loaded). Run from a
  neutral directory unless that context is wanted.
- CI or any terminal-less environment without cached credentials exits with
  `authentication required` instead of hanging.
- `--disable-slash-commands` turns off slash-command and skill expansion in
  print mode.

## Safety

`--dangerously-skip-permissions` approves every tool call of the run, file
writes and shell commands included. Disposable directory, self-written
prompt, nothing sensitive within reach - and never the user's working tree.
