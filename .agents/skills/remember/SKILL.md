---
name: remember
description: >
  Extract durable knowledge from the recent conversation and write it to knowledge/,
  routed into a topic subdirectory. Use "remember everything" or "remember full
  session" to scan the entire visible conversation.
  Triggers on: "/remember", "remember this", "save to knowledge",
  "catalog this", "persist this".
argument-hint: "[optional: what to remember, or 'full session']"
---

# remember

Extract durable facts from the conversation and write them to `knowledge/`, in a topic subdirectory that fits. Everything in `knowledge/` is yours — there's no team/shared split.

**Default scope:** Recent conversation (last few exchanges).
**Full scope:** Say "remember session" / "remember everything" / "remember full session" to scan the entire visible conversation.

---

## Workflow

### 1. Scan the conversation

**Default (recent):** Look at the last few exchanges. Identify durable facts — things true beyond this session.

**Full session (explicit request):** Scan the entire visible conversation. Use when it covered multiple topics.

Look for:
- Facts and reference details worth keeping (how something works, a definition, a spec)
- Methodology lessons (what approach worked, what didn't, why)
- Domain rules and institutional knowledge
- Tool/API/system insights (auth quirks, endpoints, gotchas)

Skip:
- Transient work output (one-off results, specific numbers, file paths)
- Preferences or style corrections — update `dobby.local.md` § Preferences directly instead
- Project status updates — those belong in `hot.md` via `/jot`

### 2. Present the items

For each fact, propose a target file and route it by topic into a `knowledge/` subdirectory (create the subdirectory if it doesn't exist yet):

```
Knowledge items found:

  1. [fact] → knowledge/<topic>/<slug>.md
  2. [fact] → knowledge/<topic>/<existing-file>.md  (append)

Approve, move any by number, skip, or add.
```

Pick subdirectories that match how you think about your life/work (e.g. `finance/`, `writing/`, `health/`, `projects/`, `tools/`, `personal/`). Reuse an existing subdirectory before inventing a new one.

### 3. User approves or adjusts

The user can: "approve" · "skip 2" · "put 1 under finance" · "add: <new fact>". Adjust and re-present before writing.

### 4. Write each item

**4a. Search first.** `Grep knowledge/**/*.md` for key terms. Read the top match if relevant.

**4b. Disposition:**
- *Significant overlap* → `Edit` the existing file to append the new detail
- *No overlap* → `Write` a new file with frontmatter

**4c. Write to `knowledge/<topic>/<slug>.md`** with frontmatter:
```yaml
---
type: note
tags: [relevant, terms]
confidence: confirmed
created: YYYY-MM-DD
related: []
---
```

**4d. Update that subdirectory's `_index.md`** — add a row for the new file (create `_index.md` if the subdirectory is new). This is what makes the note discoverable at session start.

### 5. Update hot.md and rebuild index

- Invoke `/jot` to capture what was written.
- Rebuild the BM25 index: `python hooks/bm25_index.py --build`

### 6. Report

One line per item: the file written (new or appended). Done.