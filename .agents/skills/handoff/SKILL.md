---
name: handoff
description: >
  Capture full state for open topic(s) so the next session can pick up seamlessly.
  Writes under topic sections in hot.md + matching blocks in hot-detail.md.
  Topic-oriented, not session-oriented — use /remember for durable facts.
  Triggers on: "/handoff", "hand off", "handoff to next session",
  "save state", "wrap up session", "continue later".
---

# handoff

Write a structured handoff under each **open topic** that needs resume. Summary
bullet goes in `hot.md` (injected at session start); full block goes in
`hot-detail.md` (read on demand via the pointer).

---

## What to capture

Scan the conversation and extract per topic:

### Active tasks
What are we working on? What was the original request?

### Current approach
Methodology/strategy; key decisions about how to tackle it.

### What's done
Completed steps, results delivered, files written.

### What's remaining
Unfinished steps, next actions.

### File locations
All outputs, scripts, data caches — full paths.

### Open questions
Unresolved ambiguities, deferred decisions.

### Key context
Gotchas, failed approaches, non-obvious filters — anything a new session would redo without this.

---

## Format

### 1. Upsert hot.md via the jot script (preferred)

```bash
echo '{"topic":"<slug>","title":"<Display Title>","note":"<one sentence: done + next>","extra":{"Task":"…","Approach":"…","Done":"…","Remaining":"…","Files":"…","Open":"…","Context":"…"}}' | python hooks/session_capture.py --note
```

Or multi-topic: one call per topic that moved.

### 2. Manual shape (if not using the script)

**hot.md**
```
## <Display Title>
- [YYYY-MM-DD] <one sentence: what was done + key result + what's next>. → hot-detail.md#<slug>
```

**hot-detail.md**
```markdown
## <slug>
- [YYYY-MM-DD HH:MM] HANDOFF — <task name>
  - **Task:** …
  - **Approach:** …
  - **Done:** …
  - **Remaining:** …
  - **Files:** …
  - **Open:** …
  - **Context:** …
```

`<slug>` must match exactly between the hot pointer and hot-detail header
(lowercase-hyphenated, e.g. `agency-staffing`, `inst-audit`).

---

## Rules

- **Topic-primary** — not one dump per session. Multi-topic session → multiple handoffs.
- **Latest bullet under a topic wins** for "what's current"; older dated bullets are history until 7-day expiry.
- **Be comprehensive in hot-detail** — next session can skim but can't invent missing context.
- Specific examples: policy numbers, PTKs, row counts, exact dollars, non-obvious SQL.
- Full paths, not relative.
- Don't ask for confirmation — write and show what you wrote.
- **Promote Remaining to tasks.md** as open `☐` rows so morning brief surfaces them.

---

## Example

**hot.md**
```
## Installment recon audit
- [2026-06-25] Replay 99.8% match on 375K rows; diagnose 39 integrity-break rows. → hot-detail.md#inst-audit
```

**hot-detail.md**
```markdown
## inst-audit
- [2026-06-25 16:45] HANDOFF — Installment reconciliation audit
  - **Task:** Reconcile installment vs billing vs Excel
  - **Approach:** Replay billing cycle in Python at PTK level
  - **Done:** Replay script; REVERSED filter fix; 375K rows, 99.8% match
  - **Remaining:** Diagnose 39 rows with monthly_minus_coverages≠0
  - **Files:** C:\Users\…\installment_reconciliation_FULL.csv
  - **Open:** ETL bug vs expected on the 39 rows?
  - **Context:** REVERSED txns ETL'd with wrong state; VOID absent; use abs() for cancel signs
```