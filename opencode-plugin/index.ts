/**
 * dobby OpenCode plugin
 *
 * 1) Memory: shell out to Python hooks (session_init + knowledge_lookup +
 *    session_capture) so any host shares the same BM25 / hot.md path.
 *    session.idle/deleted/turn → session_capture.py buffers prompts only (no hot write).
 * 2) MCP: config hook merges $DOBBY_HOME/.mcp.json into OpenCode's mcp map (if present).
 *    dobby ships with no MCP servers by default; configure Composio or local tools later by
 *    creating .mcp.json. Heavy/optional servers can be gated behind DOBBY_MCP_FULL=1.
 *
 * DOBBY_HOME resolution (critical):
 *   1) process.env.DOBBY_HOME
 *   2) walk up from this file looking for AGENTS.md or hooks/session_init.py
 *   3) never assume ".." alone — plugin may live at ~/.config/opencode/plugins/dobby
 */
import type { Plugin } from "@opencode-ai/plugin"
import { execFileSync } from "child_process"
import {
  existsSync,
  appendFileSync,
  mkdirSync,
  realpathSync,
  readFileSync,
} from "fs"
import { dirname, join, resolve } from "path"
import { homedir } from "os"
import { fileURLToPath } from "url"

/** Optional MCPs — only loaded when DOBBY_MCP_FULL=1. Empty by default. */
const HEAVY_MCP = new Set<string>([])

type ClaudeMcpEntry = {
  type?: string
  url?: string
  command?: string
  args?: string[]
  env?: Record<string, string>
  timeout?: number
}

type OpenCodeMcpEntry = {
  type: "remote" | "local"
  url?: string
  command?: string[]
  enabled?: boolean
  timeout?: number
  environment?: Record<string, string>
}

/**
 * Convert Claude-style .mcp.json → OpenCode mcp map.
 * Canonical list lives in $DOBBY_HOME/.mcp.json (if present).
 */
function loadMcpServers(home: string): Record<string, OpenCodeMcpEntry> {
  const src = join(home, ".mcp.json")
  if (!existsSync(src)) {
    log(`mcp: no .mcp.json at ${src} (none configured)`, "debug")
    return {}
  }
  let raw: { mcpServers?: Record<string, ClaudeMcpEntry>; mcp?: Record<string, ClaudeMcpEntry> }
  try {
    raw = JSON.parse(readFileSync(src, "utf8"))
  } catch (e) {
    log(`mcp: parse fail ${src}: ${e}`, "error")
    return {}
  }
  const servers = raw.mcpServers || raw.mcp || {}
  const homeFwd = home.replace(/\\/g, "/")
  const includeFull =
    process.env.DOBBY_MCP_FULL === "1" || process.env.DOBBY_MCP_FULL === "true"
  const out: Record<string, OpenCodeMcpEntry> = {}

  const subst = (s: string) =>
    s
      .replace(/\$\{CLAUDE_PLUGIN_ROOT\}/g, homeFwd)
      .replace(/\$\{DOBBY_HOME\}/g, homeFwd)
      .replace(/\\/g, "/")

  for (const [name, entry] of Object.entries(servers)) {
    if (HEAVY_MCP.has(name) && !includeFull) continue

    if (entry.url || entry.type === "http" || entry.type === "sse" || entry.type === "remote") {
      out[name] = {
        type: "remote",
        url: subst(entry.url || ""),
        enabled: true,
        timeout: entry.timeout ?? 30_000,
      }
      continue
    }

    if (!entry.command) continue
    const command = [subst(entry.command), ...(entry.args || []).map(subst)]
    const environment: Record<string, string> = {
      DOBBY_HOME: homeFwd,
    }
    for (const [k, v] of Object.entries(entry.env || {})) {
      environment[k] = subst(String(v))
    }
    // Point local servers at ~/.dobby/.env for credentials if present.
    const envFile = join(homedir(), ".dobby", ".env")
    if (existsSync(envFile)) {
      environment.DOBBY_ENV = envFile.replace(/\\/g, "/")
    }
    out[name] = {
      type: "local",
      command,
      enabled: true,
      timeout: entry.timeout ?? 120_000,
      environment,
    }
  }

  return out
}

/** Merge .mcp.json servers into OpenCode config.mcp (in place). */
function mergeMcpIntoConfig(cfg: { mcp?: Record<string, unknown> }): string[] {
  const converted = loadMcpServers(DOBBY_HOME)
  if (!Object.keys(converted).length) return []
  if (!cfg.mcp || typeof cfg.mcp !== "object") cfg.mcp = {}
  const names: string[] = []
  for (const [name, entry] of Object.entries(converted)) {
    cfg.mcp[name] = entry
    names.push(name)
  }
  return names
}

// Default: quiet one-liners. Set DOBBY_PLUGIN_DEBUG=1 for verbose (every event, etc.).
const DEBUG = process.env.DOBBY_PLUGIN_DEBUG === "1" || process.env.DOBBY_PLUGIN_DEBUG === "true"
const LOG = join(homedir(), ".dobby", "opencode-plugin.log")

function log(msg: string, level: "info" | "debug" | "error" = "info") {
  if (level === "debug" && !DEBUG) return
  try {
    mkdirSync(dirname(LOG), { recursive: true })
    const line = `[${new Date().toISOString()}] ${msg}\n`
    appendFileSync(LOG, line, "utf8")
  } catch {
    /* ignore */
  }
}

function looksLikeDobbyRoot(dir: string): boolean {
  return (
    existsSync(join(dir, "hooks", "session_init.py")) &&
    (existsSync(join(dir, "AGENTS.md")) || existsSync(join(dir, "CLAUDE.md")))
  )
}

function resolveDobbyHome(): string {
  if (process.env.DOBBY_HOME && looksLikeDobbyRoot(process.env.DOBBY_HOME)) {
    return process.env.DOBBY_HOME
  }

  // Real path of this plugin file (follows junctions)
  let start: string
  try {
    start = dirname(realpathSync(fileURLToPath(import.meta.url)))
  } catch {
    start = typeof import.meta.dirname === "string" ? import.meta.dirname : process.cwd()
  }

  // Walk up: opencode-plugin/ → repo root, or plugins/dobby → … until found
  let dir = start
  for (let i = 0; i < 8; i++) {
    if (looksLikeDobbyRoot(dir)) return dir
    const parent = dirname(dir)
    if (parent === dir) break
    dir = parent
  }

  // Last resort: common clone path (dev machine)
  const guesses = [resolve(start, ".."), "C:/dev/dobby", join(homedir(), "dev", "dobby")]
  for (const g of guesses) {
    if (looksLikeDobbyRoot(g)) return g
  }

  log(`resolveDobbyHome FAILED start=${start} env=${process.env.DOBBY_HOME ?? ""}`)
  return process.env.DOBBY_HOME || resolve(start, "..")
}

const DOBBY_HOME = resolveDobbyHome()
log(`load DOBBY_HOME=${DOBBY_HOME} ok=${looksLikeDobbyRoot(DOBBY_HOME)} debug=${DEBUG}`)

// Cache session-init output so it's computed once and injected on every LLM call.
let sessionContext = ""
let sessionInitAttempted = false
// Per-session BM25/knowledge text: computed in chat.message, applied in system.transform
// so it never appears in the user-visible message bubble.
const pendingKnowledgeBySession = new Map<string, string>()
// Recent user prompts per session — buffered for optional resume context (not written to hot).
const sessionPrompts = new Map<string, string[]>()
const MAX_PROMPTS_PER_SESSION = 12

/** Prefer real python.exe; avoid Windows Store alias / shell hang via cmd.exe. */
function resolvePython(): string {
  const candidates = [
    process.env.PYTHON,
    process.env.VIRTUAL_ENV ? join(process.env.VIRTUAL_ENV, "Scripts", "python.exe") : "",
    process.env.VIRTUAL_ENV ? join(process.env.VIRTUAL_ENV, "bin", "python") : "",
    process.env.CONDA_PREFIX ? join(process.env.CONDA_PREFIX, "python.exe") : "",
    join(homedir(), "anaconda3", "python.exe"),
    join(homedir(), "miniconda3", "python.exe"),
    "python",
  ].filter(Boolean) as string[]
  for (const c of candidates) {
    if (c === "python" || existsSync(c)) return c
  }
  return "python"
}

const PYTHON = resolvePython()

function runPython(
  script: string,
  args: string[] = [],
  stdin?: string,
  timeoutMs = 20_000,
): string {
  const scriptPath = resolve(DOBBY_HOME, script)
  if (!existsSync(scriptPath)) {
    log(`runPython missing script=${scriptPath}`)
    return ""
  }
  // execFileSync: no cmd.exe shell (Windows ETIMEDOUT often from shell wrapper + hung stdin)
  try {
    const out = execFileSync(PYTHON, ["-u", scriptPath, ...args], {
      cwd: DOBBY_HOME,
      encoding: "utf-8",
      timeout: timeoutMs,
      env: { ...process.env, DOBBY_HOME, PYTHONUNBUFFERED: "1" },
      input: stdin ?? "",
      maxBuffer: 8 * 1024 * 1024,
      windowsHide: true,
    }).trim()
    log(`ok ${script} ${out.length}b`, "debug")
    return out
  } catch (e: unknown) {
    const err = e as { message?: string; stderr?: string; status?: number }
    log(
      `FAIL ${script} err=${err?.message ?? e} status=${err?.status ?? ""} stderr=${(err?.stderr ?? "").slice(0, 200)}`,
      "error",
    )
    return ""
  }
}

/** Lazy session init — session.created may not fire; first LLM call still gets context. */
function ensureSessionContext(): string {
  if (sessionContext) return sessionContext
  sessionInitAttempted = true
  sessionContext = runPython("hooks/session_init.py")
  if (!sessionContext) {
    log("ensureSessionContext empty after session_init")
  }
  return sessionContext
}

export const DobbyPlugin: Plugin = async () => {
  return {
    /**
     * Bundle MCP list from $DOBBY_HOME/.mcp.json into runtime config (if present).
     * Mutates OpenCode Config in place (plugin config hook returns void).
     */
    config: async (cfg) => {
      const names = mergeMcpIntoConfig(cfg as { mcp?: Record<string, unknown> })
      log(`config mcp from .mcp.json: ${names.join(", ") || "(none)"}`)
    },

    event: async ({ event }) => {
      log(`event ${event.type}`, "debug")
      const props = (event as { properties?: Record<string, unknown> }).properties || {}
      const sid = String(
        props.sessionID || props.sessionId || props.session_id || "",
      )

      if (event.type === "session.created") {
        sessionContext = runPython("hooks/session_init.py")
        log(`session.created init=${sessionContext ? sessionContext.length + "b" : "empty"}`)
        return
      }

      // session.idle / session.deleted → buffer prompts only (hot is judgment/jot-only).
      if (event.type === "session.idle" || event.type === "session.deleted") {
        if (!sid) return
        const prompts = sessionPrompts.get(sid) || []
        if (!prompts.length && event.type === "session.idle") return
        const payload = JSON.stringify({
          session_id: sid,
          reason: event.type === "session.deleted" ? "deleted" : "idle",
          source: "opencode",
          prompts,
        })
        runPython("hooks/session_capture.py", [], payload, 10_000)
        if (event.type === "session.deleted") {
          sessionPrompts.delete(sid)
          pendingKnowledgeBySession.delete(sid)
        }
        log(`session_capture buffer ${event.type} sid=${sid.slice(0, 12)} prompts=${prompts.length}`)
      }
    },

    "experimental.chat.system.transform": async (input, output) => {
      // System channel only — do not attach retrieval text to user-visible parts.
      const ctx = ensureSessionContext()
      if (ctx) output.system.push(ctx)
      const sid = input.sessionID
      let knLen = 0
      if (sid && pendingKnowledgeBySession.has(sid)) {
        const kn = pendingKnowledgeBySession.get(sid) || ""
        pendingKnowledgeBySession.delete(sid)
        if (kn) {
          output.system.push(kn)
          knLen = kn.length
        }
      }
      log(
        `inject session=${ctx ? ctx.length : 0}b knowledge=${knLen}b`,
        knLen || ctx ? "info" : "debug",
      )
    },

    "chat.message": async (input, output) => {
      // Compute retrieval here (we have the user text) but do NOT mutate output.parts —
      // that prints in the OpenCode TUI as part of the user message.
      ensureSessionContext()
      const promptText = output.parts
        .filter((p): p is Extract<(typeof p), { type: "text" }> => p.type === "text")
        .map((p) => ("text" in p ? String((p as { text: string }).text) : ""))
        .join("\n")
        .trim()

      if (!promptText) return

      // Track user prompts in-memory + disk buffer (no hot.md write).
      const sid = input.sessionID
      if (sid) {
        const list = sessionPrompts.get(sid) || []
        list.push(promptText)
        if (list.length > MAX_PROMPTS_PER_SESSION) {
          list.splice(0, list.length - MAX_PROMPTS_PER_SESSION)
        }
        sessionPrompts.set(sid, list)
        runPython(
          "hooks/session_capture.py",
          ["--buffer"],
          JSON.stringify({
            session_id: sid,
            prompt: promptText,
          }),
          8_000,
        )
      }

      const payload = JSON.stringify({ prompt: promptText, session_id: input.sessionID })
      const result = runPython("hooks/knowledge_lookup.py", [], payload, 15_000)
      if (result) {
        pendingKnowledgeBySession.set(input.sessionID, result)
        log(`lookup ${result.length}b`, "debug")
      }
    },
  }
}

// OpenCode plugin installer looks for exports["./server"] or package main
export const server = DobbyPlugin
export default DobbyPlugin
