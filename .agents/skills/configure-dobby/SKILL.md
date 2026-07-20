---
name: configure-dobby
description: >
  The single front door for setting up and repairing dobby. Idempotent, script-light,
  and detect-first: the agent probes the machine, does the mechanical work itself with
  its own tools, and asks the user only the few genuine choices — via structured
  multiple-choice, with recommended defaults pre-selected. Detects/installs missing
  runtimes (Python, Node, opencode), installs plugin deps, sets DOBBY_HOME, wires
  OpenCode, sets a permission tier, helps auth a model provider, verifies, and tells
  the user to restart. Use when the user says "set up dobby", "configure dobby",
  "onboard me", "I just cloned dobby", is on a new machine, or something is broken.
  Sub-steps: bootstrap, opencode, permissions, provider, personalize, verify.
argument-hint: "[optional: setup step or sub-task]"
---

# configure-dobby

The one skill that stands dobby up and keeps it healthy. **No install scripts** — you (the
agent) do the work directly with bash/read/write.

**Primary host: OpenCode CLI.** Claude Code / other coding-agent CLIs are optional secondary wiring that follow the same pattern (plugin/instructions/skills paths + provider auth).

## Operating principles

- **Idempotent.** Check before every action; never clobber correct state. Re-running on a
  healthy machine reports "all green" and changes nothing.
- **Detect first, ask last.** Probe the environment up front. Do everything mechanical and
  *report* it. Only genuine decisions become questions — skip any question the machine
  already answers.
- **Structured choices, good defaults.** Present decisions as multiple-choice using the
  harness's question UI, with the recommended option pre-selected so a fast user just confirms.
- **Transcribe, don't improvise.** When a step gives an exact file body or command, write
  it verbatim (substituting real paths). Never invent config shapes.
- **Be personal and warm.** Learn the user's name early and use it. "Dobby is here to help."
- **Honest about limits.** Plugin/memory only come alive *after a restart*. Say so plainly.

## Flow

```
open opencode in the cloned dobby dir
   │  (committed opencode.jsonc: skills + doctrine)
   ▼
run  configure-dobby
   0  Resolve DOBBY_HOME
   1  Detect & plan      probe machine → show board → confirm plan (1 question)
   2  Bootstrap          runtimes → plugin deps → DOBBY_HOME  (fix only gaps)
   3  Wire OpenCode      global config: plugin, instructions, skills, provider, model
   4  Permissions        pick a tier (1 question) → write global OpenCode
   5  Provider auth      Claude subscription / API key / other  (1 question)
   6  Connect tools      Composio OAuth + optional local files → .mcp.json
   7  Make it yours      optional: name/role/paths → dobby.local.md; choose a knowledge location
   8  Prove it           health board → RESTART required → welcome
```

## Argument shortcuts

| Argument | Action |
|---|---|
| _(none)_ | Full arc, detect-first |
| `list` | Print this shortcut menu |
| `bootstrap` | Runtimes + plugin deps + DOBBY_HOME only |
| `opencode` | Wire the OpenCode harness |
| `permissions` / `perms` | Re-run the permission-tier question |
| `provider` / `auth` | Set/repair the model provider auth |
| `connect` / `tools` | Connect Composio and optional local filesystem access |
| `vault` / `scaffold` | Create `knowledge/` topic folders + starter `_index.md`s |
| `verify` / `check` | Health board |
| `personalize` / `who` | Name / role / paths → `dobby.local.md` |

---

# ACT 0 — Resolve DOBBY_HOME

1. Current working directory, if it has `AGENTS.md` **and** `hooks/session_init.py` (launched in the clone — common case).
2. `$DOBBY_HOME` if set and valid.
3. Otherwise ask for the clone path.

Carry as `DOBBY_HOME`. Prefer a **non-OneDrive/non-synced** path; use **forward slashes** in JSON (`C:/dev/dobby`).

---

# ACT 1 — Detect & plan

Probe the machine (don't ask what you can detect):

- Runtimes: `python --version`, `node --version && npm --version`, `opencode --version`
- Plugin deps: does `<DOBBY_HOME>/opencode-plugin/node_modules/@opencode-ai/plugin` exist?
- Env: is the `DOBBY_HOME` user var set and correct?
- Provider auth: has the user authed a model provider? (`opencode auth list`, or `ANTHROPIC_API_KEY` in env / `~/.dobby/.env`)
- Personal overlay: does `dobby.local.md` exist?
- Knowledge location: is `<DOBBY_HOME>/knowledge` a normal directory or a junction/symlink to an external vault?

Show a compact **status board** and plan, then **one** confirm question:

> Here's what I found:
> `opencode ✓ · python ✓ · node ✓ · plugin deps ✗ · DOBBY_HOME unset · provider auth ✗`
> **Plan:** install plugin deps, set DOBBY_HOME, wire OpenCode, permissions, provider auth.
> — **`Proceed`** (recommended) · `Let me change something`

If everything is already green, say so and stop (still remind: restart if they just changed plugin/config).

---

# ACT 2 — Bootstrap (fix only gaps)

| Item | If missing |
|---|---|
| Python 3.10+ | First ask: `Do you already have Python installed somewhere?` Explain that the user can paste the path to `python.exe` (for example `C:/Users/<you>/AppData/Local/Programs/Python/Python312/python.exe` or an Anaconda `python.exe`). Offer **Install Python** as the recommended alternative; on Windows run `winget install Python.Python.3.12`, then re-detect. Set `PYTHON` to a supplied working path rather than changing PATH unnecessarily. |
| Node + npm | Require current Node LTS (currently 22.22.2+). If Node is missing or older, offer `winget install OpenJS.NodeJS.LTS`, then re-detect. |
| opencode | `winget install SST.opencode` |
| Plugin deps | `npm install --silent` inside `<DOBBY_HOME>/opencode-plugin` |
| DOBBY_HOME env | `[Environment]::SetEnvironmentVariable("DOBBY_HOME","<DOBBY_HOME>","User")` |

dobby's Python hooks are **stdlib-only** — no `pip install` required. (Optional: `pip install psutil` makes stale mode-file cleanup slightly more precise.)

If `winget` fails or needs elevation, give the exact command and continue with what you can.

---

# ACT 3 — Wire OpenCode

**Global config** — merge into `~/.config/opencode/opencode.jsonc` (create if absent).
**Merge** — never delete unrelated keys. Ensure **at least** these keys exist (paths with forward slashes):

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "plugin": ["file:///<DOBBY_HOME>/opencode-plugin"],
  "instructions": ["<DOBBY_HOME>/AGENTS.md"],
  "skills": { "paths": ["<DOBBY_HOME>/.agents/skills"] }
}
```

- **No `mcp` by default** — dobby ships with none. `configure-dobby connect` creates the Composio configuration in `<DOBBY_HOME>/.mcp.json`; the plugin merges it at startup.
- Add `"<DOBBY_HOME>/dobby.local.md"` to `instructions` **only if that file exists** (Act 6).
- `file:///` URLs: three slashes + absolute path, e.g. `file:///C:/dev/dobby/opencode-plugin`.
- The committed repo-root `opencode.jsonc` already sets a default `model`; the global config's provider auth (Act 5) is what makes it run.

---

# ACT 4 — Permissions

Present **one** question, **Guarded** pre-selected:

> **How should dobby handle permission prompts?**
> - **`Guarded`** (recommended) — free local work; ask before git `push`/`reset`/`commit --amend`/`rebase` and any outward send.
> - **`Cautious`** — ask before any write (edit/bash) and outward sends.
> - **`Dangerously`** — auto-approve everything.

Write **OpenCode → global** `~/.config/opencode/opencode.jsonc` `permission`:

```jsonc
// Guarded
"permission": {
  "edit": "allow",
  "bash": { "*": "allow", "git push*": "ask", "git reset*": "ask", "git commit --amend*": "ask", "git rebase*": "ask" }
}
// Cautious
"permission": {
  "edit": "ask", "bash": "ask", "external_directory": "ask"
}
// Dangerously
"permission": "allow"
```

If you later wire tool MCPs that send email/messages, add `"ask"` entries for those tool names under Guarded. Confirm the choice in plain language.

---

# ACT 5 — Provider auth

dobby is provider-agnostic. Present **one** question, **Claude subscription** pre-selected:

> **Which model provider should dobby use?**
> - **`Claude subscription`** (recommended) — run `opencode auth login` → Anthropic → sign in with Claude Pro/Max. No per-token billing.
> - **`Anthropic API key`** — paste a key; written to `~/.dobby/.env` as `ANTHROPIC_API_KEY` (or `opencode auth login`). Pay-per-use.
> - **`Other provider`** — OpenAI/etc.: `opencode auth login`, then set `"model"` in the global config accordingly.

Mechanics:
- **Claude subscription / API key:** guide `opencode auth login` (interactive; the user completes the browser/paste step). For a raw API key the user prefers to store in a file, write `~/.dobby/.env` with `ANTHROPIC_API_KEY=<value>` (create dir/file; never re-print the secret).
- **Model:** the committed `opencode.jsonc` defaults to a Claude model. If the user picked a non-Anthropic provider, update `"model"` in the global config to match (e.g. `openai/gpt-...`).
- Never print secrets back after writing them.

---

# ACT 6 — Connect your tools (optional — easy to defer)

This is what turns dobby from a smart notebook into a Friday that can *act*. Composio is the default: one remote MCP with managed OAuth for Gmail, Google Calendar, Google Drive, Dropbox, GitHub, and many other services. It is optional and can be done later: "We can wire tools now, or later — just run `configure-dobby connect` when you're ready."

dobby has **no MCP tools by default**. Wiring is: create `<DOBBY_HOME>/.mcp.json` from `.mcp.json.example` → authenticate Composio in the browser → connect individual services on demand. The starter configuration includes Composio and an optional filesystem server.

Ask whether to connect Composio now:

> **Connect Composio now?**
> - **`Connect Composio`** (recommended) — this is how dobby connects to Google services (Gmail, Calendar, Drive) as well as Dropbox, GitHub, and other apps. Browser OAuth grants access only to the services you choose.
> - **`Filesystem only`** — local access to selected folders with no account connection.
> - **`Do this later`** — leave MCP tools unconfigured.

For `Connect Composio`:
1. Copy `.mcp.json.example` to `.mcp.json`, retaining the `composio` server and adding `filesystem` only if selected.
2. Run `opencode mcp auth composio`. This launches the browser OAuth flow.
3. Tell the user: "A browser window is open. Sign in to Composio and approve access to OpenCode." Wait for them to complete it; never claim authentication succeeded without `opencode mcp list` confirming it.
4. Verify with `opencode mcp list`. Tell the user they can now ask dobby to connect specific apps, for example: "Connect Gmail with Composio" or "Connect Dropbox with Composio." Each service presents its own consent screen and scopes.

For `Filesystem only`, copy the filesystem entry with the user-selected folders. If they defer, leave `.mcp.json` absent (dobby runs tool-free, local-first). Restart OpenCode after changing `.mcp.json`.

---

# ACT 7 — Make it yours (optional)

## 7A — Personal overlay

**`dobby.local.md` is optional** (deltas only). Do **not** seed placeholders.

> Want personal touches now, or take defaults?
> — **`Take defaults`** (recommended) · `Add my name, role & paths`

- **Defaults:** no `dobby.local.md`; continue.
- **Touches:** short interview (name, role/fluency, output paths) → copy `dobby.local.example.md` to `dobby.local.md`, fill only those fields, add its path to OpenCode `instructions`.

## 7B — Choose the knowledge base

Ask before creating any starter folders:

> **Where should dobby keep durable knowledge?**
> - **`Dobby knowledge folder`** (recommended) — keep private notes in `<DOBBY_HOME>/knowledge`.
> - **`Link an existing knowledge base`** — use an Obsidian vault or another folder you already maintain.

For `Link an existing knowledge base`:

1. Ask for the absolute folder path. Explain that every future `/remember` and knowledge-intake write will go there; for example, `C:/Users/<you>/Dropbox/ObsidianVault`.
2. Verify the path exists and is a directory. Do not create a new external knowledge-base folder without a separate confirmation.
3. Inspect `<DOBBY_HOME>/knowledge`. If it contains real notes, show the files and ask how to merge them. Never overwrite a same-named vault file. If it contains only dobby's empty starter scaffold, do not copy that scaffold into the external vault.
4. Replace `<DOBBY_HOME>/knowledge` with a directory link to the chosen folder: Windows uses `cmd /c mklink /J`; macOS/Linux use `ln -s`. Preserve any pre-existing local files until the user explicitly approves their deletion or move.
5. Rebuild with `python hooks/bm25_index.py --build`, run one relevant query, and state that the external vault is now the source of truth. Its contents remain untracked by Git.

## 7C — Scaffold the knowledge vault

`knowledge/` starts blank. Offer to create a starter topic structure so there are obvious homes for notes (and so session-start injection has index maps to load). It's gitignored (personal), so this only affects the local/Dropbox copy.

Present a **multi-select**, recommended set pre-checked:

> **Which knowledge topics should I set up?** (create folders now; you can add more anytime)
> - **people** ✓ — who's who, relationships, open favors
> - **projects** ✓ — multi-session personal projects
> - **finance** ✓ — accounts map, tax rules you use, big decisions
> - **home** ✓ — house, vendors, warranties, maintenance
> - **health** ✓ — non-sensitive logs, goals, providers
> - **travel** ✓ — preferences, frequent itineraries, loyalty numbers
> - **learning** — things you're studying; notes dobby-as-teacher builds
> - **work** — job/career, colleagues, recurring processes
> - **preferences** — style/process overflow that outgrows `dobby.local.md`

For each chosen topic, create `knowledge/<topic>/_index.md` with a header + an empty table:

```markdown
# <Topic>

<one-line purpose>. One file per subject as content grows.

| File | Subject | Retrieve when |
|---|---|---|
| *(empty)* | | |
```

Skip any that already exist (idempotent). Then rebuild the index: `python hooks/bm25_index.py --build`. If the user declines, leave `knowledge/` as-is — notes can create folders on the fly via `/remember`.

---

# ACT 8 — Prove it & welcome

| Check | How |
|---|---|
| DOBBY_HOME | resolves; has `AGENTS.md` + `.agents/skills/` |
| Python | `python -c "import json, re, math"` (stdlib sanity) |
| Plugin deps | `opencode-plugin/node_modules/@opencode-ai/plugin` exists |
| Global OpenCode | plugin path + instructions + skills paths present |
| Provider auth | `opencode auth list` shows a provider, or a key is set |

**Hard requirement:** tell the user to **quit and restart OpenCode** so the plugin and memory hooks load.

Close warmly; if name known:

```
══════════════════════════════════════════════
   <name>, Dobby is here to help.
   Restart OpenCode, then try: good morning
══════════════════════════════════════════════
```
