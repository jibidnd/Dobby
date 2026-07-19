---
name: knowledge-lint
description: >
  Health check dobby's knowledge and memory layers. Finds orphan files (not in any
  _index.md), dead wikilinks, stale index entries, frontmatter gaps, inconsistent
  cross-references, and stale memory. Generates a lint report and optionally
  auto-fixes safe issues. Triggers on: "lint", "health check", "check knowledge",
  "knowledge audit", "vault health", "find orphans", "check the wiki".
argument-hint: "[optional: scope or focus area]"
---

# knowledge-lint: Health Check

Run lint periodically (every 10-15 knowledge writes, or weekly) or on demand. Report findings before fixing anything — ask before auto-fixing.

---

## What to check

Work through these in order across both layers (`knowledge/` and `memory/`).

### 1. Orphan files (knowledge/ only)

Files in `knowledge/` that are not listed in any `_index.md`. These exist but are invisible to the routing system — the BM25 index will find them, but explicit routing won't.

**How to check:**
1. `Glob knowledge/**/*.md` — collect all .md files (excluding `_index.md` files themselves, `.obsidian/`, `.claude/`, `.claudian/`, `query_examples/`)
2. `Read` each `_index.md` file
3. Compare: any file whose stem or relative path doesn't appear in any `_index.md` is an orphan

**Severity:** MEDIUM — file works via BM25 but misses explicit routing. Fix by adding a row to the correct `_index.md`.

### 2. Dead wikilinks

Wikilinks (`[[Note Name]]`) that reference a file that doesn't exist in the vault.

**How to check:**
1. `Grep` for `\[\[` across `knowledge/**/*.md`
2. For each wikilink target, check if a matching file exists (by stem, case-insensitive)

**Severity:** LOW — cosmetic, but accumulates. Fix by creating stubs or removing dead links.

### 3. Stale index entries

Entries in `_index.md` files that reference files that have been renamed or deleted.

**How to check:**
1. `Read` each `_index.md`
2. Extract file references (from the table or bullet list)
3. Check if each referenced file exists

**Severity:** HIGH — stale index entries cause the injection hook to reference missing files, which silently fails. Fix by removing the stale row.

### 4. Frontmatter gaps (knowledge/ only)

Knowledge files missing required frontmatter fields. Required fields depend on file type:

| Type | Required fields |
|---|---|
| Knowledge note | `type`, `tags`, `created` |
| Memory files | `type`, `created` |

**How to check:**
1. `Read` frontmatter of each file
2. Check for required fields

**Severity:** LOW for memory files, MEDIUM for knowledge files (affects discoverability).

### 5. Inconsistent cross-references

Files using `see_also:` instead of `related:` in frontmatter (the standard is `related:`). Also check for one-directional links: if A lists B in `related:`, does B list A?

**How to check:**
1. `Grep` for `see_also:` across `knowledge/**/*.md`
2. For each file with `related:`, check if referenced files link back

**Severity:** LOW — cosmetic. Fix by standardizing on `related:` and adding reciprocal links.

### 6. Stale hot cache

No entries in `memory/hot.md` within the last 7 days — sessions would start cold.

**How to check:**
1. `Read` `memory/hot.md`
2. Find the most recent `## YYYY-MM-DD` date header
3. If the most recent date is >7 days ago, or the file is empty, flag as stale

**Severity:** MEDIUM — stale hot cache means sessions start without recent context.

### 7. Long-lived hot-detail entries

HANDOFF entries in `memory/hot-detail.md` older than 4 days — approaching the 7-day expiry and likely worth promoting or explicitly dropping before they auto-purge.

**How to check:**
1. `Read` `memory/hot-detail.md`
2. Find all `## YYYY-MM-DD-slug` section headers
3. Parse the date from each header; flag any >4 days old

**Severity:** LOW — informational. Candidates for /distill-memory before they expire.

### 8. Empty subdirectories

Knowledge subdirectories that have an `_index.md` but no content files, or content files but no `_index.md`.

**How to check:**
1. `Glob` each knowledge subdirectory
2. Check for `_index.md` + at least one content file

**Severity:** LOW — structural. Fix by creating `_index.md` or removing empty dirs.

### 9. BM25 index freshness

Check if `memory/.search_index.json` exists and is recent (< 24 hours old).

**How to check:**
1. Check file existence and modification time

**Severity:** LOW — index auto-rebuilds at session start; this catches edge cases.

---

## Lint report format

Create the report at `memory/lint-report-YYYY-MM-DD.md` (memory, not knowledge — lint reports are ephemeral).

```markdown
---
type: meta
created: YYYY-MM-DD
tags: [lint, health-check]
---

# Lint Report — YYYY-MM-DD

## Summary
- Knowledge files scanned: N
- Memory files scanned: M
- Issues found: X (H high, M medium, L low)
- Auto-fixable: Y

## HIGH — Stale Index Entries
- `knowledge/finance/_index.md` references `roth-conversion.md` — file does not exist

## MEDIUM — Orphan Files
- `knowledge/travel/` — 7 PDFs, no `_index.md`, not referenced anywhere
- `knowledge/writing/style-notes.md` — not in `_index.md`

## MEDIUM — Frontmatter Gaps
- `knowledge/finance/tax-brackets-2026.md` — missing `tags`, `created`

## LOW — Inconsistent Cross-References
- 4 files use `see_also:` instead of `related:`
- 12 one-directional links (A→B but not B→A)

## LOW — Dead Wikilinks
- `[[roth-conversion]]` in `knowledge/finance/retirement-plan.md`

## LOW — Aged Notes
- `memory/hot-detail.md` — a topic block 45 days old, worth promoting to `knowledge/`

## INFO
- Hot cache: updated 2 days ago (OK)
- BM25 index: updated today (OK)
- Directories without _index.md: `knowledge/regulatory/naic/`
```

---

## Auto-fix policy

**Safe to auto-fix (with confirmation):**
- Adding missing `_index.md` rows for orphan files
- Standardizing `see_also:` → `related:`
- Adding missing frontmatter fields with placeholder values
- Rebuilding BM25 index

**Requires human review:**
- Deleting stale index entries (the file might have been renamed, not deleted)
- Removing dead wikilinks (the target page might need to be created)
- Promoting aged discoveries to knowledge
- Resolving one-directional links (the reciprocal link might not make sense)

Always show the report first. Then ask: "Should I auto-fix the safe issues, or do you want to review each one?"

---

## Integration with the librarian

After lint, if there are long-lived hot-detail entries (check 7), suggest: "There are N HANDOFF entries >4 days old in hot-detail.md. Run /distill-memory to review before they auto-expire."

The librarian handles bulk promotions and reorganization — lint only identifies candidates.