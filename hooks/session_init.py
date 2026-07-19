"""SessionStart hook — initialize dobby's knowledge and memory systems.

One script that handles everything at session start:
  1. Validate setup (DOBBY_HOME)
  2. Clean hot.md and memory/handoffs/ — delete entries older than 7 days; warn on entries expiring within 3 days
  3. Inject hot.md (recent session context)
  4. Build BM25 search index over knowledge/ and memory/
  5. Inject knowledge _index.md files (domain routing maps — auto-discovered)
  6. Inject skills/_index.md (skill trigger phrases; path may be .agents/skills via link)
"""
from __future__ import annotations

import os
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# DOBBY_HOME points at the repo so memory/ and knowledge/ resolve even when the
# hook runs from a plugin cache copy rather than the source tree.
_dobby_home = os.environ.get("DOBBY_HOME", "")
ROOT = Path(_dobby_home) if _dobby_home and Path(_dobby_home).is_dir() else Path(__file__).parent.parent
KNOWLEDGE_DIR = ROOT / "knowledge"
MEMORY_DIR = ROOT / "memory"
HOT_PATH = MEMORY_DIR / "hot.md"
TASKS_PATH = MEMORY_DIR / "tasks.md"
HANDOFFS_DIR = MEMORY_DIR / "handoffs"

# Cap on total _index.md injection (~4k tokens).
INDEX_CAP_CHARS = 4000 * 4

# Hot.md entries older than this are purged. Life spans weeks/months, not a work
# sprint — a month keeps open loops warm without hoarding. Long-cycle commitments
# should be promoted to tasks.md (due dates) or knowledge/ rather than left to expire.
HOT_MAX_AGE_DAYS = 30

# Entries older than this (but not yet purged) get an expiry warning (7-day heads-up).
HOT_WARN_DAYS = HOT_MAX_AGE_DAYS - 7

# Pattern matching date headers in hot.md: ## YYYY-MM-DD
DATE_HEADER_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")

# ── Visual output ───────────────────────────────────────────────────────

def _print_banner() -> None:
    print("┌────────────────────────────────────────────┐")
    print("│  dobby  ·  session starting                │")
    print("└────────────────────────────────────────────┘")


def _print_session_ready(n_files: int, n_domains: int) -> None:
    print(f"\n✔ dobby is here to help — {n_files} files indexed, {n_domains} knowledge domains loaded")


# ── Session greeting ──────────────────────────────────────────────────

def _is_last_day_of_month(now: datetime) -> bool:
    return (now + timedelta(days=1)).month != now.month


def _session_greeting(now: datetime) -> str | None:
    month, day, hour, minute, weekday = now.month, now.day, now.hour, now.minute, now.weekday()
    mins = hour * 60 + minute

    if month == 12 and day == 31:
        return "Last day of the year. Make it count."
    if _is_last_day_of_month(now):
        return "Month-end. Let's tie off the loose ends."
    if month == 1 and day == 1:
        return "New year, clean slate. Dobby is ready."
    if day == 1:
        return "New month, who dis."
    if mins < 8 * 60:
        return "Up before 8. Bold strategy."
    if mins >= 22 * 60:
        return "Burning the midnight oil. Dobby is here."
    if mins >= 17 * 60:
        return "Still here? Respect."
    if weekday == 4 and hour >= 15:
        return "Friday afternoon. Almost free."
    if weekday == 0:
        return "Monday. Let's ride."
    return None


def print_session_greeting() -> None:
    greeting = _session_greeting(datetime.now())
    if greeting:
        print(f"\n{greeting}")


# ── Setup validation ──────────────────────────────────────────────────

def validate_setup() -> None:
    issues: list[str] = []

    dobby_home = os.environ.get("DOBBY_HOME", "")
    if not dobby_home or not Path(dobby_home).is_dir():
        issues.append("DOBBY_HOME not set or missing")

    if issues:
        print(f"⚠ dobby setup incomplete — run /dobby:configure-dobby to fix: {', '.join(issues)}")


# ── Hot cache cleanup ─────────────────────────────────────────────────

def clean_hot_cache() -> None:
    """Expire hot.md bullets older than HOT_MAX_AGE_DAYS.

    Supports topic-primary shape (## Topic / - [YYYY-MM-DD] …) and legacy
    date-header shape (## YYYY-MM-DD / - [HH:MM] …). Drops empty topic sections
    and legacy **auto** session lines.
    """
    if not HOT_PATH.exists():
        return

    try:
        content = HOT_PATH.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    cutoff = datetime.now() - timedelta(days=HOT_MAX_AGE_DAYS)
    bullet_date_re = re.compile(
        r"^- \[(\d{4}-\d{2}-\d{2})(?:[ T]\d{1,2}:\d{2})?\]\s+"
    )
    auto_tag_re = re.compile(r"\*\*auto\*\*\s+`sid=")
    lines = content.splitlines()

    keep_lines: list[str] = []
    # For legacy date headers: whole section may be stale
    legacy_section_stale = False
    expired_count = 0
    current_header: str | None = None
    section_buf: list[str] = []

    def flush_section() -> None:
        nonlocal expired_count
        if current_header is None:
            return
        # Drop empty sections and pure-date legacy headers with no bullets left
        bullets = [ln for ln in section_buf if ln.strip().startswith("- ")]
        if not bullets and DATE_HEADER_RE.match(f"## {current_header}"):
            return
        if not bullets and not section_buf:
            return
        if not keep_lines or keep_lines[-1].strip():
            pass
        keep_lines.append(f"## {current_header}")
        keep_lines.append("")
        keep_lines.extend(section_buf)
        if section_buf:
            keep_lines.append("")

    for line in lines:
        hm = re.match(r"^## (.+?)\s*$", line)
        if hm:
            flush_section()
            current_header = hm.group(1).strip()
            section_buf = []
            m = DATE_HEADER_RE.match(line)
            if m:
                try:
                    legacy_section_stale = (
                        datetime.strptime(m.group(1), "%Y-%m-%d") < cutoff
                    )
                except ValueError:
                    legacy_section_stale = False
            else:
                legacy_section_stale = False
            continue

        if current_header is None:
            # preamble before first header — keep non-empty
            if line.strip():
                keep_lines.append(line)
            continue

        if auto_tag_re.search(line):
            expired_count += 1
            continue

        if line.strip().startswith("- "):
            if legacy_section_stale:
                expired_count += 1
                continue
            bm = bullet_date_re.match(line.strip())
            if bm:
                try:
                    bdate = datetime.strptime(bm.group(1), "%Y-%m-%d")
                    if bdate < cutoff:
                        expired_count += 1
                        continue
                except ValueError:
                    pass
            section_buf.append(line.rstrip())
        elif not line.strip():
            continue
        else:
            section_buf.append(line.rstrip())

    flush_section()

    if expired_count > 0:
        HOT_PATH.write_text("\n".join(keep_lines).strip() + "\n", encoding="utf-8")


def clean_handoff_files() -> None:
    """Delete handoff files older than HOT_MAX_AGE_DAYS from memory/handoffs/."""
    if not HANDOFFS_DIR.exists():
        return
    cutoff = datetime.now() - timedelta(days=HOT_MAX_AGE_DAYS)
    for path in HANDOFFS_DIR.glob("*.md"):
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-", path.name)
        if m:
            try:
                file_date = datetime.strptime(m.group(1), "%Y-%m-%d")
                if file_date < cutoff:
                    path.unlink()
            except ValueError:
                pass


# ── Expiry warning ───────────────────────────────────────────────────

def warn_expiring_handoffs() -> None:
    """Print a warning for handoff files expiring within 3 days."""
    if not HANDOFFS_DIR.exists():
        return
    warn_cutoff = datetime.now() - timedelta(days=HOT_WARN_DAYS)
    expiring: list[str] = []
    for path in sorted(HANDOFFS_DIR.glob("*.md")):
        m = re.match(r"^(\d{4}-\d{2}-\d{2})-(.+)\.md$", path.name)
        if m:
            try:
                file_date = datetime.strptime(m.group(1), "%Y-%m-%d")
                if file_date < warn_cutoff:
                    expires = (file_date + timedelta(days=HOT_MAX_AGE_DAYS)).strftime("%Y-%m-%d")
                    expiring.append(f"{m.group(2)} (created {m.group(1)}, expires {expires})")
            except ValueError:
                pass
    if expiring:
        items = ", ".join(expiring)
        print(f"\n⚠ IMPORTANT — surface this to the user in your first response:")
        print(f"HANDOFF entries expiring soon: {items} — run /distill-memory to review or promote before they auto-delete")


# ── Hot cache injection ───────────────────────────────────────────────

def inject_hot_cache() -> None:
    if HOT_PATH.exists():
        try:
            content = HOT_PATH.read_text(encoding="utf-8", errors="replace").strip()
            if content:
                print(f"\n--- memory/hot.md (recent context) ---\n{content}")
        except OSError:
            pass


# ── Task file cleanup & injection ─────────────────────────────────────

# Completed/cancelled tasks older than this are purged from tasks.md.
TASK_DONE_MAX_AGE_DAYS = 10

# Regex matching a task row: | ☐/☑/✗ | task | category | due | added | progress |
_TASK_ROW_RE = re.compile(
    r"^\|\s*([☐☑✗])\s*\|"   # status
    r"[^|]*\|"               # task
    r"[^|]*\|"               # category
    r"[^|]*\|"               # due
    r"\s*(\d{4}-\d{2}-\d{2})\s*\|"  # added date (captured)
)


def clean_tasks_file() -> None:
    """Purge completed/cancelled tasks older than TASK_DONE_MAX_AGE_DAYS."""
    if not TASKS_PATH.exists():
        return
    try:
        lines = TASKS_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return

    cutoff = datetime.now() - timedelta(days=TASK_DONE_MAX_AGE_DAYS)
    keep: list[str] = []
    purged = 0

    for line in lines:
        m = _TASK_ROW_RE.match(line)
        if m and m.group(1) in ("☑", "✗"):
            try:
                added = datetime.strptime(m.group(2), "%Y-%m-%d")
                if added < cutoff:
                    purged += 1
                    continue
            except ValueError:
                pass
        keep.append(line)

    if purged:
        TASKS_PATH.write_text("\n".join(keep).rstrip() + "\n", encoding="utf-8")


def warn_overdue_tasks() -> None:
    """Print overdue open tasks so dobby surfaces them in the first response."""
    if not TASKS_PATH.exists():
        return
    try:
        lines = TASKS_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return

    today = datetime.now().strftime("%Y-%m-%d")
    overdue: list[str] = []

    for line in lines:
        m = _TASK_ROW_RE.match(line)
        if not m or m.group(1) != "☐":
            continue
        # Extract the due date (4th column)
        cols = [c.strip() for c in line.split("|")[1:-1]]
        if len(cols) >= 4:
            due = cols[3]
            if due not in ("—", "") and due < today:
                overdue.append(f"  - {cols[1]} (due {due}, {cols[2]})")

    if overdue:
        items = "\n".join(overdue)
        print(f"\n⚠ IMPORTANT — surface this to the user in your first response:")
        print(f"Overdue tasks:\n{items}")


# ── BM25 index build ─────────────────────────────────────────────────

def build_bm25_index() -> int:
    try:
        import importlib.util
        bm25_path = ROOT / "hooks" / "bm25_index.py"
        if not bm25_path.exists():
            return 0
        spec = importlib.util.spec_from_file_location("bm25_index", bm25_path)
        bm25 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bm25)
        index = bm25.build_index()
        bm25.save_index(index)
        return int(index.get("num_docs", 0))
    except Exception:
        return 0


# ── Knowledge index injection ─────────────────────────────────────────

def inject_knowledge_indexes() -> int:
    if not KNOWLEDGE_DIR.exists():
        return 0

    pieces: list[str] = []
    total = 0

    # Auto-discover every knowledge subdirectory that has an _index.md.
    subdirs = sorted(p.name for p in KNOWLEDGE_DIR.iterdir() if p.is_dir())
    for subdir_name in subdirs:
        index_path = KNOWLEDGE_DIR / subdir_name / "_index.md"
        if not index_path.exists():
            continue
        content = index_path.read_text(encoding="utf-8", errors="replace")
        block = f"--- knowledge/{subdir_name}/_index.md ---\n{content}"
        if total + len(block) > INDEX_CAP_CHARS:
            break
        pieces.append(block)
        total += len(block)

    if pieces:
        print("\n\n".join(pieces))
    return len(pieces)


# ── Skills index injection ────────────────────────────────────────────

def inject_skills_index() -> None:
    # Canonical AAIF path first; fall back to Claude plugin link (skills/ → .agents/skills)
    path = ROOT / ".agents" / "skills" / "_index.md"
    if not path.exists():
        path = ROOT / "skills" / "_index.md"
    if not path.exists():
        return
    try:
        content = path.read_text(encoding="utf-8", errors="replace").strip()
        if content:
            print(f"\n--- skills/_index.md ---\n{content}")
    except OSError:
        pass


# ── Mode file cleanup ─────────────────────────────────────────────────

# Hard upper bound — handles PID reuse edge case and crashed sessions
# that left no PID in the file (legacy global mia_mode.json).
_MODE_MAX_AGE_SECONDS = 24 * 3600


def _is_pid_alive(pid: int) -> bool:
    """Return True if the process with the given PID is still running."""
    try:
        import psutil  # type: ignore
        return psutil.pid_exists(pid)
    except ImportError:
        pass
    # Windows fallback via ctypes (no elevated permissions needed for same-user)
    try:
        import ctypes
        SYNCHRONIZE = 0x100000
        handle = ctypes.windll.kernel32.OpenProcess(SYNCHRONIZE, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        pass
    return True  # can't determine — assume alive


def clean_stale_mode_files() -> None:
    """Delete session-scoped mode files whose owning process has exited.

    Skips the current session's file. Falls back to a 24-hour age limit
    for files that don't contain a PID (legacy) or where the PID check
    is unavailable.
    """
    import tempfile

    current_session = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    tmp = Path(tempfile.gettempdir())
    now = datetime.now().timestamp()

    candidates = [*tmp.glob("dobby_mode_*.json"), tmp / "dobby_mode.json"]
    for path in candidates:
        if not path.exists():
            continue
        if current_session and path.name == f"dobby_mode_{current_session}.json":
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            pid = data.get("pid")
            if pid and _is_pid_alive(int(pid)):
                continue  # owning process still running
        except Exception:
            pass
        # No PID, dead PID, or unreadable — fall back to age limit
        try:
            if path.stat().st_mtime < now - _MODE_MAX_AGE_SECONDS:
                path.unlink()
        except Exception:
            pass


# ── Main ──────────────────────────────────────────────────────────────

def main() -> None:
    _print_banner()
    print_session_greeting()
    validate_setup()
    clean_hot_cache()
    clean_handoff_files()
    clean_tasks_file()
    clean_stale_mode_files()
    warn_expiring_handoffs()
    warn_overdue_tasks()
    inject_hot_cache()
    n_files = build_bm25_index()
    n_domains = inject_knowledge_indexes()
    inject_skills_index()
    _print_session_ready(n_files, n_domains)


if __name__ == "__main__":
    main()