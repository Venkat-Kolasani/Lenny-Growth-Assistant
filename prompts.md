# prompts.md

Copy-paste prompts for kicking off or continuing a coding-agent session on this repo. Each one bakes in the read-first / write-back protocol from `AGENTS.md` so it happens by default, not only when remembered.

## 1. New session start (most common — use this one)

```
Before doing anything else, read AGENTS.md in full, then read the top entry of
handoff.md to see exactly where the last session left off. If anything in
handoff.md conflicts with PRD.md, architecture.md, or design.md, flag it to me
before proceeding instead of guessing which is current.

Then work on the "Next up" list from handoff.md's top entry, in order.

Rules while working:
- Don't deviate from a decision already locked in AGENTS.md without saying so
  and appending a rationale entry to docs.md.
- If you hit a non-obvious fork (a trade-off, a library choice, a workaround),
  write the "why" to docs.md as you make the call, not after.

Before you finish this session:
1. Update handoff.md with a new top entry (done / current state / next up /
   open decisions), following the template at the top of that file.
2. Make sure docs.md reflects any decision you made that isn't already there.
3. Append this session to agent-transcripts/ (see agent-transcripts/README.md),
   including failed attempts and how you corrected them. Strip secrets. This
   is assignment deliverable #6 — do not skip it or save it for submission day.
4. Tell me in plain language what changed and what's next.
```

## 2. Mid-task continuation (same session, just context-compacted)

```
Re-read handoff.md's top entry and AGENTS.md's "already decided" list before
continuing — don't re-derive decisions that are already settled there.
Continue the in-progress task from where handoff.md says it stopped.
Same end-of-session rule applies: update handoff.md and docs.md before wrapping
up, and append this session to agent-transcripts/ (failed attempts included,
secrets stripped). That folder is a graded deliverable — capturing it later is
how it ends up empty.
```

## 3. Starting a specific PRD milestone

```
Read AGENTS.md and handoff.md first. Then implement <milestone, e.g. "the
ingestion pipeline from architecture.md §3"> exactly as specified there —
if the spec is ambiguous on something, make the smallest reasonable call,
note it in docs.md, and keep going rather than stalling on it.

When done: update handoff.md with what's now working and what the logical
next milestone is, add tests per test-plan.md for whatever you just built,
and append this session to agent-transcripts/ (failed attempts included,
secrets stripped — assignment deliverable #6).
```

## 4. Debugging / fixing something broken

```
Read AGENTS.md for the locked-in stack decisions and architecture.md for how
this component is supposed to behave, then investigate <symptom>. Check
test-plan.md's resilience section — this may be a case that's supposed to be
handled explicitly rather than crash.

Once fixed: add a regression test, log the root cause in docs.md if it
reveals a gap in the original design (not just "fixed a bug"), and append
the failed attempt plus the correction to agent-transcripts/. Failed
attempts are explicitly part of the required deliverable.
```

## 5. End-of-day wrap-up (run this even if the task above already did most of it)

```
Confirm handoff.md's top entry accurately reflects the current state of the
repo (what runs, what's tested, what's not built yet), that docs.md has an
entry for every non-obvious decision made this session, and that
agent-transcripts/ has a write-up for this session (including failed attempts,
secrets stripped). If any of the three is stale, fix it now before ending.
```
