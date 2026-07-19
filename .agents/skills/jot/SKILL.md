---
name: jot
description: >
  Quick capture into topic-based working memory (hot.md + hot-detail.md).
  Judgment only â€” jot when there are numbers, decisions, outcomes, or files
  worth resuming; skip chitchat. Triggers on: "/jot", "jot this",
  "jot that down", "note this", "quick save", "log this".
argument-hint: "[optional: note text]"
---

# jot

Write **analyst-grade substance** into the topic log. Nothing is auto-written to
`hot.md` from raw prompts â€” only explicit jots (and handoffs) land there.

## When to jot

**Yes** after substantive work: numbers, decisions, outcomes, file paths, gotchas,
status changes on an open thread.

**No** for chitchat, pure Q&A with nothing to resume, or "test".

Multi-topic session â†’ one jot per topic that moved (same note shape, different `topic`).

## What to do

1. Pick a **stable topic** (slug-friendly). Prefer an existing hot.md section title
   if the work continues that thread. One-offs â†’ topic `misc` (or omit â†’ Misc).
2. Distill **one dense note**: key numbers, decision, outcome, files, gotchas.
   Front-load the takeaway (hot line is capped ~160 chars).
3. Run (from `$DOBBY_HOME` or with `DOBBY_HOME` set):

```bash
echo '{"topic":"<slug-or-title>","note":"<dense note>"}' | python hooks/session_capture.py --note
```

Optional fields:
- `"title": "Agency staffing â†’ Charles"` â€” display header (defaults from topic)
- `"detail": false` â€” hot-only (no hot-detail append); default true
- `"extra": {"Files":"â€¦","Open":"â€¦"}` â€” structured sub-bullets in hot-detail

4. Report the JSON stdout (`hot_line`, `anchor`/`slug`). Don't hand-edit hot files.

## What the script does

- Upserts **today's** bullet under `## <topic>` in `hot.md` (same-day rewrite;
  older days under the topic stay as history).
- Moves that topic section to the top.
- Appends a dated entry under `## <slug>` in `hot-detail.md` (when detail=true).
- Strips any leftover legacy `**auto** sid=` lines on write.

## Rules

- **Do not** create parallel lines for the same topic â€” upsert via the script.
- Include specific numbers, not vague summaries.
- Don't ask for confirmation â€” run and show what was written.
- Full structured resume (Remaining / Files / Open) â†’ `/handoff` (same topic model,
  denser detail). Mid-session substance â†’ jot.