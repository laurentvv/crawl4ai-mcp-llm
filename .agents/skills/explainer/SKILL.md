---
name: explainer
description: Turn a dense result, system, error or architecture into the cheapest artifact the user can actually process - an escalation ladder from controlled plain English (ASD-STE100, or 80% of it) through diagrams (Mermaid, ASCII, SVG) to interactive single-file HTML pages, and on explicit request an explainer video. Use when an answer risks being long or dense, when the user asks to explain, summarize or visualize something, says they do not understand, re-asks the same question, or asks for a diagram, a page, a demo or an explainer for a topic. Pick the lowest rung that answers the question; escalate when prose stops working.
---

# Explainer

As agents do more work on their own, the human job moves up to supervising
and understanding what came back. Raw prose is the most expensive format to
process: when an explanation grows long or dense, build a small custom
artifact instead - disposable, made for one question, worth more than a page
of text.

## The ladder

Start at the lowest rung that can answer the question; move up one rung when
the user re-asks, says they do not understand, or the prose would run past a
screen. Never jump straight to the top without a signal.

1. **Controlled English** - simplified technical English in the spirit of
   ASD-STE100 (apply "80% of the way" when the full spec reads too stiff):
   short sentences, one topic per sentence, active voice, plain verbs, no
   idiom, measured numbers over adjectives. This stays the baseline voice
   for every rung above.
2. **Diagram** - when structure is the question (flow, timeline, states,
   dependencies, who calls what). Mermaid where a forge renders it, ASCII
   when the artifact must survive a terminal or a diff, SVG for layout
   control. One diagram answers exactly one question; label every box with
   the real names.
3. **Interactive single-file HTML page** - when the user must explore rather
   than read: tabs, hover detail, sliders, step-through of a sequence.
   Self-contained by default - inline CSS and JS, no CDN, no network, no
   build step - so the file opens directly in a browser on any machine.
   A throwaway artifact, never a maintained app.
4. **Explainer video, on explicit request only** - storyboard first (scenes,
   narration text, what appears when) and the user approves it before any
   render. Local path first: animated HTML canvas plus capture, or the
   pipeline the repository already has; narration through a local TTS when
   available. An external API (voice, video) only on explicit user
   instruction - the key comes from an environment variable and never lands
   in code, logs or the artifact itself.

## Rules

- Artifacts are disposable: write them under `scratch/` or the location the
  repository declares; never wire them into the build or the docs unless
  asked.
- The artifact accompanies the chat, it does not replace it: deliver it with
  a short summary in controlled English and the path to the file.
- Numbers shown in an artifact are measured or read from the source
  material, never invented to make the picture nicer.
- A reusable insight goes to the project state files (dated entry) like any
  other finding.

## Outputs

- the chosen artifact under `scratch/` (or the declared location): text in
  controlled English, a diagram, an HTML page or, on request, a video
- a short chat summary plus the artifact path
- one rung kept in reserve: the next format to try if the user is still lost
