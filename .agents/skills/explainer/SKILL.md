---
name: explainer
description: Turn a dense result, system, error or architecture into a custom artifact the user can actually process. The default artifact is a high-quality interactive single-file HTML page (self-contained, no CDN, no build step); diagrams (Mermaid, ASCII) only where HTML cannot render; controlled plain English (ASD-STE100 spirit) for chat answers; an explainer video on explicit request. Use when the user asks to explain, summarize, visualize or show something, says they do not understand, re-asks, or asks for a page, a diagram, a demo or an explainer. A markdown file is never the deliverable when a page is possible.
---

# Explainer

As agents do more work on their own, the human job moves up to supervising
and understanding what came back. Raw prose is the most expensive format to
process, and models are now strong at frontend: when something deserves more
than a chat answer, build a small custom artifact - disposable, made for one
question, a real page rather than a wall of text.

## The ladder

1. **Controlled English** - simplified technical English in the spirit of
   ASD-STE100 (apply "80% of the way" when the full spec reads too stiff):
   short sentences, one topic per sentence, active voice, plain verbs, no
   idiom, measured numbers over adjectives. This is the voice of EVERY
   answer, chat included; prose alone is fine only for short replies.
2. **Diagram** - for surfaces that cannot render a page: terminal output,
   diffs, PR comments, doc embeds. Mermaid where a forge renders it, ASCII
   in a terminal. A diagram is a bonus inside a chat answer, never the
   deliverable when a page is possible.
3. **Interactive single-file HTML page - the default artifact.** Whenever
   the request deserves an artifact, build a real page: deliberate layout,
   real typography, color, and interaction (hover detail, filters, tabs,
   step-through). Self-contained: inline CSS and JS, no CDN, no network,
   no build step - it opens directly in a browser on any machine. A
   throwaway artifact, never a maintained app. A markdown or plain text
   file is never an acceptable substitute.
4. **Explainer video, on explicit request only** - storyboard first (scenes,
   narration text, what appears when) and the user approves it before any
   render. Local path first: animated HTML canvas plus capture, or the
   pipeline the repository already has; narration through a local TTS when
   available. An external API (voice, video) only on explicit user
   instruction - the key comes from an environment variable and never lands
   in code, logs or the artifact itself.

## Quality bar

- Design it, do not dump it: a page with no styling decisions (default
  HTML look, no spacing system, no hierarchy) is not done. Rebuild it.
- Inspect before delivering: screenshot the rendered page and look at it.
  The artifact ships only after visual inspection - verified means seen.
- Start at the highest rung the surface allows: the page by default, a
  diagram only where a page cannot live, prose for short chat replies.
- "Make it better", a re-ask or "I do not understand" means ONE rung up,
  not a polish of the same rung.

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

- the artifact under `scratch/` (or the declared location): by default the
  interactive HTML page; a diagram where no page can live; a video on
  explicit request
- a screenshot kept as evidence of the visual inspection
- a short chat summary plus the artifact path
- one rung kept in reserve: the next format to try if the user is still lost
