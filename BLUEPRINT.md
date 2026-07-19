# dobby — product blueprint

**Tagline:** *Dobby is here to help.*  
**Home:** `C:\dev\dobby` · **Env:** `DOBBY_HOME` · **Git:** local-only (no remote for now)  
**Host:** OpenCode CLI primary · Claude optional later  

---

## 1. Product thesis

dobby is your **Friday** (as in Tony Stark's) — one assistant that does *anything* you ask. Life ops **and** thinking partner **and** builder, on one substrate. No fixed job description.

**Continuity is the substrate, not the ceiling.** dobby remembers who you are and what's open so every session starts warm — and that memory serves whatever you need: running your day, teaching you something, thinking a problem through, writing, crunching numbers, shipping code, planning a trip.

| Loop | Meaning |
|---|---|
| **Know** | Who you are, constraints, open loops (`dobby.local.md` + memory + knowledge) |
| **Surface** | What needs attention today / this week |
| **Act** | Draft, schedule, book, file, follow up — *or* teach, analyze, build, decide |
| **Close** | Jot outcomes so the next session starts warm |

Chat is the UI. Continuity is the substrate. **Range is the product** — equally strong at life-ops and intellectual work; the lanes (teacher/writer/quant/counsel/engineer/coach) are hats dobby wears on demand, not a separate mode you have to invoke.

### Action ladder (always)

```
answer → draft → schedule hold → send / book / pay
```

Higher rungs always need explicit confirmation. Never invent availability, balances, or bookings when tools aren’t connected — say so and offer a paste path.

---

## 2. Architecture (locked)

### Two-tier model — no standing agent roster

| Tier | What | When |
|---|---|---|
| **1 — dobby** | One generalist; flexes any lane via framing (hats) | Default for everything |
| **2 — ephemeral workers** | Task tool, role-primed on the fly, isolated context | Only when items are genuinely independent / research-heavy |

**Agents buy isolation + critic independence — not expertise.** Same model, different prompt. No `agents/*.md` files to maintain.

### “Team” capability (lightweight — not deploy-team)

1. **Doctrine rule** in `AGENTS.md` — break down large work; fan out only when independent; **confirm before multi-worker fan-out**
2. **`critic` skill** — tear apart *outputs* with fresh eyes (sibling to `grilling` for *plans*). **Independence is structural: the critic spawns a fresh-context Task worker** given only the artifact — never an in-thread "critique myself" pass (that anchors on the maker's reasoning = the weakness it exists to fix). In-thread critique is allowed only when someone *else* wrote the work.
3. **No** `deploy-team` / `deploy-team-collaborative` in dobby

Optional later: thin `hats/*.md` (20-line framing overlays: teacher, writer, quant, counsel, engineer, coach) — **skills/hats, not spawned processes**.

### What dobby is *not*

- Not an enterprise/work runtime  
- Not a multi-specialist firm  
- Not auto-booking without confirmation  
- Not a team knowledge vault  

---

## 3. Folder tree (target)

```
C:\dev\dobby\                          # DOBBY_HOME
├── AGENTS.md                          # doctrine (always loaded)
├── BLUEPRINT.md                       # this file
├── README.md                          # human setup (short)
├── dobby.local.example.md             # template → copy to dobby.local.md
├── dobby.local.md                     # gitignored personal overlay
├── opencode.jsonc                     # skills.paths + instructions (no standing agents)
├── .gitignore
│
├── .agents/skills/                    # canonical skills (AAIF)
│   ├── _index.md
│   ├── configure-dobby/
│   ├── personal-assistant/            # day brief, tasks, drafts
│   ├── jot/ · handoff/ · remember/
│   ├── distill-memory/ · knowledge-intake/ · knowledge-lint/
│   ├── grilling/ · critic/
│   ├── generate-report/ · mode/
│   └── (hats optional later)
│
├── skills/                            # junction → .agents/skills (local discovery)
├── .opencode/                         # junction / machine wiring (gitignored)
│
├── hooks/                             # session_init, session_capture, knowledge_lookup, bm25
├── opencode-plugin/                   # OpenCode adapter (memory inject; lean MCP later)
│
├── memory/                            # gitignored — working state
│   ├── hot.md                         # topic log (latest bullet wins)
│   ├── hot-detail.md                  # deep resume by topic slug
│   ├── tasks.md                       # personal task list
│   └── handoffs/                      # optional denser dumps
│
├── knowledge/                         # durable personal notes (GITIGNORED — personal; Dropbox-backed)
│   ├── _index.md                      # root map
│   ├── people/                        # who is who, open favors
│   ├── projects/                      # multi-session personal projects
│   ├── finance/ · health/ · home/ · travel/
│   └── preferences/                   # only if too big for dobby.local.md
│
└── outputs/                           # optional local outputs (or path in dobby.local.md)
```
---

## 4. Skill list

### Ship / keep (core)

| Skill | Role |
|---|---|
| `configure-dobby` | Setup / repair front door |
| `personal-assistant` | Day brief, tasks, drafts (local-first; tools when wired) |
| `jot` | Topic log after substance |
| `handoff` | Resume state for open topics |
| `remember` | Durable → `knowledge/` (no team PR) |
| `distill-memory` | Promote hot → knowledge |
| `knowledge-intake` | Ingest files/URLs into vault |
| `knowledge-lint` | Orphans, dead links |
| `grilling` | Stress-test **plans** before build |
| `critic` | Stress-test **outputs** after build (spawns worker) |
| `mode` | Temporary voice toggle |
| `generate-report` | Self-contained writeup |

### Optional hats (later — framing only)

`teacher` · `writer` · `quant` · `counsel` · `engineer` · `coach`  
= short prompt overlays or skill stubs, **not** Task subagent types.

### MCP (deferred — dobby is built *assuming* tools, wired when convenient)

Ships with **no MCP** (empty at start). A documented `.mcp.json.example` stubs the recommended stack; `configure-dobby connect` walks setup. dobby runs local-first without any of it.

**Recommended stack (Robert's):**

| Connector | Server | Auth | Notes |
|---|---|---|---|
| Cloud apps | Composio Connect MCP | browser OAuth | One remote MCP connects Gmail, Calendar, Contacts, Drive, Dropbox, GitHub, and other apps on demand |
| Files / notes / vault | **Filesystem MCP** on the Dropbox + Obsidian-vault folders | none | **Plain files — no Obsidian plugin.** Low-friction default |
| Booking/forms | Playwright/browser | — | Higher-risk (drives a real browser); add last, for the top action-ladder rung |

Setup sequence: Composio → Filesystem = the common Friday stack with browser OAuth and no manually managed API keys.

**Mobile:** OpenCode has **no native mobile app** — TUI, desktop app, IDE extension, web, and `/share` (read-only links). All target the *host* machine, so local Dropbox files remain available through the filesystem MCP.

**Alternatives:** keep local filesystem-only access for a minimal setup. Add a specialist MCP only when Composio does not cover a required service.

---

## 5. Memory model (personal-only)

**Everything personal is gitignored.** git tracks only the dobby *product* (skills, hooks, doctrine, config). `memory/`, `knowledge/`, and `dobby.local.md` are all gitignored — backup comes from the repo living inside a synced folder (Dropbox), not git. This removes the "sensitive-durable data has no home" problem: all of `knowledge/` is private by default, no separate vault tier needed.

| Layer | Path | Bar | Lifetime |
|---|---|---|---|
| **Working** | `memory/hot.md` + `hot-detail.md` | Judgment-only jot after substance | **30-day** expiry (set in `session_init.py`) |
| **Tasks** | `memory/tasks.md` | Proactive add/update | Until done / backlog |
| **Durable** | `knowledge/**` | Facts true beyond this month (gitignored) | Permanent until edited |
| **Preferences** | `dobby.local.md` | “always / never / from now on” | Permanent |

**Rules**

- Auto hooks **buffer only** — never write hot  
- `/jot` under topic or **Misc**; multi-topic sessions jot each topic that moved  
- `/remember` → personal knowledge only (no team PR offer)  
- Preference capture → `dobby.local.md` immediately  
- **Promotion reflex:** a hot bullet that's really a long-cycle commitment → promote it (dated → `tasks.md`, durable → `knowledge/`); never rely on the 30-day window to carry a 6-month horizon  
- **Recency:** BM25 half-life = **180d** (gentle — a personal fact's age barely predicts relevance)  
- Seed empty topic *names* in hot as life fills them: Home, Health, Finance, Travel, People, Projects, Misc  

### knowledge/ routing (personal)

| Dir | Put here |
|---|---|
| `people/` | Relationships, contact context, open asks |
| `projects/` | Multi-session personal projects |
| `finance/` | Tax rules *you* use, accounts map (no secrets in git if sensitive — use local-only notes) |
| `health/` | Non-sensitive logs / goals (careful with medical advice framing) |
| `home/` | House, vendors, warranties |
| `travel/` | Preferences, frequent itineraries |
| `preferences/` | Overflow style/process (prefer `dobby.local.md` first) |

---

## 6. AGENTS.md skeleton

Live file: [`AGENTS.md`](./AGENTS.md). Must always include:

1. **Who dobby is** — warm, direct, proactive, honest; success = user’s  
2. **Minimize tokens / build once**  
3. **Fan-out doctrine** — single-thread default; confirm before multi-worker  
4. **Critic** — offer fresh-context review on significant outputs  
5. **Memory** — knowledge vs memory; judgment-only jot; personal only  
6. **Guardrails** — no fabricate; confirm outward/irreversible; verify  
7. **Action ladder** — draft free; send/book confirm  
8. **Pointers** — `dobby.local.md`, hot, tasks, configure-dobby, plain `git pull`

---

## 7. dobby.local.md (personal overlay)

Template: `dobby.local.example.md`. Suggested sections:

```markdown
# Personal overlay
## Who I am
- Name, timezone, work hours, quiet hours

## Paths
- DOBBY_HOME, outputs base, misc working files

## Preferences
- Communication style, planning rules
- Booking rules (e.g. never before 9am)
- Defer = next Monday; Backlog = no due date

## Integrations (when wired)
- Mail / calendar source of truth
- What may leave the machine (LLM API only vs Google/Outlook)
```

---

## 8. Open choices (decide at configure / first week)

1. **LLM auth** — personal Anthropic / OpenAI / other  
2. **Calendar SoT** — Google vs Outlook vs local  
3. **Tasks** — `tasks.md` only vs external sync  
4. **Hot expiry** — 14d vs 30d  
5. **Claude dual-host** — now vs never  
6. **Remote git** — stay local vs private remote later  

---

## 9. Success metric (informal)

Not a KPI dashboard — one gut-check after two weeks:

> **Do you reach for dobby unprompted, and does it save you from re-explaining yourself?**

If no, something's wrong (stale brief, memory not sticking, or it's just Claude-with-a-file). Watch for the failure signal: you stop trusting an output after it's wrong/stale twice.

---

## 10. Hosting & sync

### Now — laptop-primary (single instance, one brain)

dobby runs on the **laptop**, where your files and projects live. It does *everything* — life ops, thinking, **and** project/code work. **Do not split coding off to Claude Code** — that's the multiple-context tax dobby exists to kill; dobby is an OpenCode runtime and codes just fine with your memory + doctrine loaded. Laptop is the source of truth; **nothing to sync.**

Mobile (optional, only while the laptop is awake + on Tailscale):

```
OPENCODE_SERVER_PASSWORD=<strong> opencode serve --hostname 0.0.0.0 --port 4096
```

- **Tailscale** on laptop + phone; point the mobile OpenCode client at the laptop's tailnet IP:4096.
- Reachable only when the laptop is on/connected — fine for most of the day.

### Later — add a hosted mirror (always-on mobile)

> **Full step-by-step runbook: [`docs/hosting.md`](docs/hosting.md)** — host picks, VPS setup, private git remote, Tailscale, Syncthing, `opencode serve` systemd unit, backup, smoke tests.

A cheap VPS (**$4–6/mo, 1 vCPU / 1–2 GB** — the LLM runs via API, so the box stays light) as a **second body sharing one brain**:

| What | Sync mechanism |
|---|---|
| Product (skills, hooks, plugin, AGENTS, config) | **git** — pull on both |
| Personal content (`memory/` + `knowledge/`) | **Syncthing** (peer-to-peer folder mirror, laptop ↔ VPS) |
| Projects / code | **not synced** — stay laptop-only; VPS/mobile is for life + thinking, not code |

One brain, two bodies. Use one at a time to avoid Syncthing `.sync-conflict` copies of `hot.md` (recoverable if it happens). **Syncthing** = free, open-source, private peer-to-peer continuous folder sync — no cloud account, no storage cap.

### Access hardening
Never expose `opencode serve` raw on the public internet. **Tailscale** (private mesh) is the default; if you must go public, **Cloudflare Tunnel + Access + `OPENCODE_SERVER_PASSWORD` + TLS**.

### Smoke tests before trusting a served/hosted setup
1. **Memory plugin under `opencode serve`** — the `chat.message` / `system.transform` hooks run server-side and *should* inject memory headless; verify they actually do.
2. **Headless provider auth** — an API key is easiest; for Claude-subscription OAuth, auth on a desktop and copy `~/.local/share/opencode/auth.json` to the host.

### Backup
`memory/` + `knowledge/` are gitignored, so git doesn't protect them. Syncthing gives a live second copy; add **restic/rclone → a bucket** for real versioned backup.

---

*Apply this file at scaffold time. Prefer editing BLUEPRINT.md when product intent changes; keep AGENTS.md short (runtime only).*
