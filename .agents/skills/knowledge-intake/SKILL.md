---
name: knowledge-intake
description: >
  Structured pipeline for ingesting source material into the knowledge vault.
  Two modes: interactive (guided walkthrough with user approval at each step) and
  express (auto-extract and file with minimal interaction). Handles local files,
  folders, URLs, PDFs, and images. Updates indexes, log, and hot cache.
  Invoke when pointed at a document, folder, URL, or any content worth capturing.
  Triggers on: "ingest", "intake", "process this", "add this to knowledge",
  "read and file this", "knowledge intake", "just ingest it", "express ingest".
argument-hint: "[file path, URL, or topic to ingest]"
---

# knowledge-intake

A structured pipeline for getting source material into dobby's knowledge vault. The source goes in, atomic knowledge notes come out, indexes are updated, and the hot cache reflects the change. Nothing is silently lost.

---

## Two modes

| Mode | Trigger | Behavior |
|---|---|---|
| **Interactive** (default) | "ingest this", "intake", or no flag | Guided walkthrough: discover → offer angles → explore with domain subagents → propose notes → user approves each → write |
| **Express** | "just ingest it", "express ingest", or `--express` | Read source → auto-extract facts → auto-determine routing → write → report what was created |

Interactive is default for new domains or complex source material. Express is for known-shape content (e.g., another table doc, another state's regulatory filing) where the pattern is established.

Both modes invoke `/jot` and update the relevant `_index.md` files after writing.

---

## Source detection

On invocation, determine the source type from the argument (or ask if absent):

- **Local file** — `Read` the file directly
- **Local directory** — `Glob` for all files, then `Read` for content
- **Web URL** — `WebFetch` the page; save cleaned content for processing
- **Single PDF** — `Read` with `pages:` parameter (max 20 pages per call; start with table of contents or pages 1–3)
- **Image** — `Read` the image (processed natively); describe contents and extract text
- **No argument** — ask: "What source would you like to explore? Paste a file path or web URL."

Narrate what was detected before proceeding.

---

## Interactive mode

### 1. Discover

Map the source without reading full content. Goal: understand scope before committing.

**For directories:** `Glob` for all files; group by extension; note date signals; list subfolders with counts. Output: "This folder has 18 monthly reports (2023–2025), a methodology PDF, and a few one-off memos."

**For single documents:** Read TOC or first 2–3 sections only. Output: "This is a 42-page product guide covering eligibility rules, coverage options, and underwriting exceptions."

### 2. Offer angles

Surface 3–5 specific angles based on the actual content — not generic categories. Phrase as concrete questions or topics.

> "Here are some directions we could go:
> 1. **Methodology evolution** — what changed in triangle selection across the periods
> 2. **Ongoing concerns** — issues flagged repeatedly that were never closed
> 3. **Coverage eligibility rules** — specific rules from the reference section
>
> Tell me which to explore, or describe something else."

### 3. Explore

Dive into selected angles. For research-heavy or independent angles, fan out parallel workers (Task tool) in isolated context, each primed for the relevant lane (e.g. a researcher for source-gathering, a quant for the numbers). Otherwise synthesize directly. See AGENTS.md "Fan out only when it earns its keep."

### 4. Propose notes

As knowledge surfaces, identify distinct knowledge atoms. Display as a table:

| # | Title | Target | One-line description |
|---|---|---|---|
| 1 | [note title] | `knowledge/<topic>/` | [one-line description] |
| 2 | [note title] | `knowledge/<topic>/` | [one-line description] |

Ask: "Keep all, drop any by number, or edit before adding?"

Accumulate confirmed notes across all angles.

### 5. Write

On user approval:
1. Write each note using the librarian's routing table and format conventions (see `agents/knowledge-librarian.md`)
2. Update each subdirectory's `_index.md`
3. Invoke `/jot` to record the ingest (source, notes created/updated, key insight)
4. Report: one line per note written — title and where it landed

---

## Express mode

For known-shape content where the interactive walkthrough is overkill.

### Pipeline

1. **Read** the source completely
2. **Extract** knowledge atoms automatically:
   - Schema facts → catalog file format (grain, join chain, key columns, gotchas)
   - Methodology → prose with callouts for key insights
   - Regulatory → structured reference with jurisdiction, effective dates, requirements
   - Business rules → tagged with domain and confidence level
3. **Route** each atom to the correct `knowledge/` subdirectory using the routing table
4. **Check for conflicts** — if a target file already exists:
   - Read the existing file
   - Merge new content with existing (extend, don't overwrite)
   - Flag contradictions with `> [!contradiction]` callouts
5. **Write** all notes
6. **Update** all `_index.md` files for affected subdirectories
7. **Invoke `/jot`** to capture what was created and updated
8. **Report** what was created and updated

### Express mode guard

Even in express mode, the pipeline:
- Never overwrites existing notes without merging
- Flags contradictions explicitly (doesn't silently replace old claims)
- Reports everything it did (so you can spot-check)
- Uses `confidence: unconfirmed` for auto-extracted facts unless the source is authoritative

---

## Contradiction handling

When new information contradicts an existing knowledge file:

On the existing file, add:
```markdown
> [!contradiction] Conflicts with <source>
> Existing claim: X. New source says: Y.
> Needs resolution — check dates, context, primary sources.
```

On the new note, reference it:
```markdown
> [!contradiction] Contradicts [[Existing Note]]
> This source says Y, but existing knowledge says X.
```

Never silently overwrite old claims. Flag and let the user decide.

---

## Context window discipline

- Read `memory/hot.md` first — it may already have relevant context
- Read the relevant `_index.md` before creating notes — avoid duplicates
- Read only 3–5 existing files per ingest for conflict checking
- Keep individual knowledge notes to 100–300 lines; split if longer

---

## What not to do

- Do not modify source files — sources are immutable reference material
- Do not create duplicate notes — always check indexes and search before creating
- Do not skip the log entry — every ingest must be recorded
- Do not skip the hot cache update — it keeps future sessions fast
- Do not write to `knowledge/` without routing through the established directory structure