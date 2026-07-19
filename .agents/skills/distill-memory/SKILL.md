---
name: distill-memory
description: >
  Review Claude /memory and dobby hot.md for items worth promoting to permanent
  knowledge/. Single-pass, interactive â€” summarize by topic, expand on demand,
  execute only on explicit approval.
  Triggers on: "/distill-memory", "distill memory", "clean up memory",
  "review memory", "promote memory", "catalog memory".
---

# distill-memory

Single-pass memory review. Summarize by knowledge topic, expand on demand, execute on explicit approval.

---

## Step 1: Collect

Read everything in one shot:
- `memory/hot-detail.md` (HANDOFF entries)
- `memory/hot.md` (recent entries)
- All Claude `/memory` files (scan `~/.claude/projects/` for memory directories matching the current user's paths)
- Read `dobby.local.md` Â§ Preferences to detect existing coverage; Grep relevant `knowledge/` subdirectories

## Step 2: Summarize by topic

Synthesize everything into a **topic-grouped list**. Each line is a knowledge tidbit or decision â€” not a source file or entry type. Sources (which memory file, HANDOFF, hot.md entry it came from) are secondary metadata, surfaced only when the user asks to expand.

Format:

```
<Topic or fact>  â†’  DELETE / MERGE / KEEP / TEAM  [one-line reason]
```

Example:

```
Planner bucket routing rules  â†’  DELETE   [covered in dobby.local.md Â§ Preferences â†’ Planner]
dobby dev: confirm before executing  â†’  DELETE   [covered in dobby.local.md Â§ Preferences â†’ Working preferences]
opencode junction gotcha: never rm -rf  â†’  DELETE   [stale, sidekick work deferred]
FRED API key still pending  â†’  KEEP   [open TODO in hot.md]
Knowledge routing: personal/ vs general/  â†’  MERGE â†’ dobby.local.md Â§ Preferences â†’ Knowledge vault   [new rule, not yet there]
Endorsement reversal bug in MT_Vehicles  â†’  TEAM â†’ knowledge/data/   [schema gotcha, affects all analysts]

Type "expand <topic>" for sources and full detail, adjust any item, or "approve" to execute.
```

**Routing rules:**
- Facts any team member would hit (schema gotchas, methodology, domain rules) â†’ TEAM â†’ `knowledge/<subdirectory>/`
- User-specific preferences, org context, one-off results â†’ MERGE â†’ `dobby.local.md` Â§ Preferences (or a new personal note in `knowledge/personal/`)
- Already covered in dobby.local.md Â§ Preferences or knowledge/ â†’ DELETE
- Stale / completed / deferred work â†’ DELETE
- Still active project or open TODO â†’ KEEP

## Step 3: Interactive

Respond to natural language â€” expand topics, adjust dispositions, answer questions. Do **not** execute until you receive explicit, clear approval ("approve", "looks good, go", "do it").

Common inputs:
- `"expand <topic>"` / `"tell me more about 3"` â†’ show full source content and detail for that topic
- `"keep X"` / `"change that to team"` â†’ adjust a disposition
- `"approve"` / `"looks good"` â†’ execute everything as shown

Re-present the list after any adjustments. Never execute mid-conversation.

## Step 4: Execute

On approval, process in order:

**DELETE:** Remove Claude `/memory` file(s). Prune corresponding entries from `MEMORY.md`. Remove hot.md sections/entries. Remove hot-detail.md sections.

**MERGE (PERSONAL):** Append to `dobby.local.md` Â§ Preferences (or write a new personal note in `knowledge/personal/` if the topic warrants its own file). Update `knowledge/personal/_index.md` if adding a new file. Delete the source memory file(s).

**MERGE (TEAM):** Before any git operations, show a summary and ask for PR confirmation:

```
Team KB proposals (N items):

  Branch: knowledge/propose-<slug>
  â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”â€”
  â€¢ knowledge/<domain>/<file>.md  (new file / append)

  Create PR? (y / edit / skip)
```

On confirmation:

```bash
git checkout -b knowledge/propose-<slug>
# write each target file
git add knowledge/<paths>
git commit -m "knowledge: <one-line description>"
git push -u origin knowledge/propose-<slug>
gh pr create --draft \
  --title "knowledge: <one-line description>" \
  --body "Proposed from /distill-memory.

**Items:** N facts (list titles)
**Source:** Claude /memory + hot.md
**Targets:** knowledge/<paths>

Promote or close."
```

If `git push` fails with a permissions error, print the proposed file contents and say: "You don't have push access â€” share this with the repo owner to add it."

Report the PR URL inline, then delete the source memory files.

**KEEP:** Leave as-is.

## Step 5: Rebuild and report

Rebuild BM25 index: `python hooks/bm25_index.py --build`

One line per action:
- "deleted N memory files, pruned N hot.md entries"
- "merged N items into dobby.local.md Â§ Preferences"
- "wrote knowledge/personal/<file>.md"
- "PR: <url>"