# Design — The Lenny Growth Assistant

## 1. Principles

Three rules the UI answers to, in priority order:

1. **Provenance is never optional.** If a claim is grounded, its citation is visible without a click. Trust is the entire point of this product; burying the receipt defeats it.
2. **The artifact is the destination, chat is the path.** The Artifact Viewer isn't a secondary panel bolted onto a chatbot — the layout treats it as co-equal to chat from the first screen, because a session that never produces one hasn't done its job (PRD §2.2).
3. **Clarity over cleverness.** No unexplained iconography, no state changes without a visible cause. An evaluator should understand what happened by looking at the screen, not by reading the code.

## 2. Information architecture

```
┌─────────────┬─────────────────────────────┬───────────────────────┐
│  Sessions    │        Chat thread          │    Artifact Viewer     │
│  sidebar     │                              │                       │
│              │  [model: Groq ▾]  [+ new]   │   (empty until an     │
│  - Session 1 │                              │    artifact exists)   │
│  - Session 2 │  user / assistant turns,     │                       │
│  - ...       │  citations inline under      │   Markdown | HTML     │
│              │  each grounded answer        │   tabs when multiple  │
└─────────────┴─────────────────────────────┴───────────────────────┘
```

Three columns on desktop: session history, chat, artifact. The model toggle lives in the chat header, not buried in settings — the brief explicitly requires it be visible, not just configurable.

## 3. Key interaction states

- **Empty session** — a short prompt suggesting a real question type ("Ask about onboarding, pricing, or activation — or say 'write me an essay on...'"), not a blank box. Sets expectations for both skills, not just Q&A.
- **Streaming response** — tokens stream in; citations render as soon as retrieval resolves, before generation finishes, so the source is visible even mid-answer.
- **Grounded answer** — inline citation chips (guest name + episode) under the response; clicking one opens the source link.
- **Insufficient evidence** — a visually distinct (not alarming) state: plain text stating the transcripts don't cover this, plus one suggested adjacent topic that is covered. Never a generic "I don't know."
- **Artifact ready** — the Artifact Viewer panel animates in / becomes populated; a persistent "open artifact" affordance if the user is on a narrow viewport and the panel is collapsed.
- **Model switch** — an explicit confirmation chip ("Now using Ollama (local) · llama3.2:3b") appended to the thread itself, not just a header change — so the transcript itself documents which model answered which turn.
- **Error states** (each has a distinct, human-readable message, not a stack trace):
  - Groq rate-limited → "Cloud model is rate-limited, retrying in Ns…" with visible retry countdown.
  - Ollama unreachable → "Local model isn't running — start Ollama or switch to cloud."
  - Model timeout → "The model didn't respond in time — retry, or switch provider." Distinct from unreachable: the service was contacted, it just never finished.
  - Empty retrieval → same visual language as "insufficient evidence" above.
  - DB unreachable → a top-level banner, not a broken chat pane.

## 4. Responsive behavior

- **Desktop (≥1024px):** three-column layout as above.
- **Tablet (768-1023px):** sessions sidebar collapses to an icon rail; chat + artifact remain side by side.
- **Mobile (<768px):** single column, tab-switch between Chat and Artifact (artifact tab shows a badge when a new one lands while the user is on Chat). Sessions sidebar becomes a slide-over.

## 5. Accessibility

- Full keyboard navigation: tab order follows sessions → chat input → artifact viewer; a visible focus ring throughout (no `outline: none` without a replacement).
- Citations are real links with descriptive text (`"View source: episode with {guest}"`), not bare icons — reachable and meaningful to a screen reader.
- Streaming responses use an `aria-live="polite"` region so assistive tech announces new content without interrupting mid-read.
- Color is never the only signal for state (error/success/insufficient-evidence states pair color with an icon and text label) — covers color-vision-deficient users and holds up under the contrast checks below.
- Text and interactive elements meet WCAG AA contrast minimums against both light backgrounds (chat) and the artifact preview surface.
- Model-switch and error states are announced via `aria-live`, not just visually rendered, so they aren't silently missed.

## 6. Visual design decisions

Plain, functional, and deliberately not "default AI chatbot template" — generic gradient-hero-plus-bubble-chat is the single most common look across the other 20 Lenny projects (PRD §2.4), so distinguishing the visual language from that pattern is itself part of standing out. Concretely: a restrained neutral palette with a single accent color reserved for citations and the active-model indicator (so it carries meaning, not decoration), a monospace treatment for artifact code/HTML previews to visually separate "generated work product" from "chat," and generous whitespace over dense chrome. Where useful, this is a good place to run the build through a frontend-polish pass (e.g. the `frontend-design` skill available in this workspace, or a tool like Impeccable) specifically to catch generic-AI-template tells before the demo — cheap insurance against the UI reading as templated, which is one of the two lightest-weight things (docs being the other) separating a strong submission from a merely-working one.
