"""Topic-based session memory (hot.md + hot-detail.md).

Judgment-only writes to hot — nothing mechanical from raw prompts.

  - Auto hooks (Stop / SessionEnd / idle / turn): buffer user prompts only;
    never write hot.md. Buffer cleared on real session end.
  - /jot and /handoff: agent decides topic + note → upsert under that topic.

hot.md shape (topic-primary):
  ## Agency staffing → Charles
  - [2026-07-15] Delivered; await reply → hot-detail.md#agency-staffing

hot-detail.md shape (same slug):
  ## agency-staffing
  - [2026-07-15 14:02] Delivered email…
    - **Files:** …
    - **Open:** …

Usage:
  echo '{"topic":"agency-staffing","note":"..."}' | python hooks/session_capture.py --note
  echo '{"session_id":"…","prompt":"…"}' | python hooks/session_capture.py --buffer
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

_dobby = os.environ.get("DOBBY_HOME", "").strip()
ROOT = Path(_dobby) if _dobby and Path(_dobby).is_dir() else Path(__file__).parent.parent
MEMORY_DIR = ROOT / "memory"
HOT_PATH = MEMORY_DIR / "hot.md"
HOT_DETAIL_PATH = MEMORY_DIR / "hot-detail.md"
PROMPT_BUF_DIR = MEMORY_DIR / ".session_prompts"
MAX_BUFFERED_PROMPTS = 12

DATE_HEADER_RE = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$")
AUTO_TAG_RE = re.compile(r"\*\*auto\*\*\s+`sid=([^`]+)`")
LEGACY_DETAIL_ANCHOR_RE = re.compile(
    r"^## (\d{4}-\d{2}-\d{2})-auto-([a-zA-Z0-9_-]+)\s*$"
)
TOPIC_HEADER_RE = re.compile(r"^## (.+?)\s*$")
BULLET_DATE_RE = re.compile(r"^- \[(\d{4}-\d{2}-\d{2})(?:[ T]\d{1,2}:\d{2})?\]\s+(.*)$")

MAX_LINE_CHARS = 280
MAX_HOT_NOTE_CHARS = 160
MISC_SLUG = "misc"
MISC_TITLE = "Misc"


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _now_hm() -> str:
    return datetime.now().strftime("%H:%M")


def _short_sid(session_id: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9_-]", "", session_id or "")
    return s[:12] if s else "unknown"


def slugify(topic: str) -> str:
    t = (topic or "").strip().lower()
    t = re.sub(r"['\"]", "", t)
    t = re.sub(r"[^a-z0-9]+", "-", t)
    t = re.sub(r"-+", "-", t).strip("-")
    return t[:64] if t else MISC_SLUG


def title_from_slug(slug: str) -> str:
    if slug == MISC_SLUG:
        return MISC_TITLE
    return slug.replace("-", " ").strip().title()


def _buf_path(session_id: str) -> Path:
    return PROMPT_BUF_DIR / f"{_short_sid(session_id)}.jsonl"


def append_prompt(session_id: str, prompt: str) -> None:
    text = (prompt or "").strip()
    if not text or not session_id:
        return
    PROMPT_BUF_DIR.mkdir(parents=True, exist_ok=True)
    path = _buf_path(session_id)
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"t": _now_hm(), "p": text}, ensure_ascii=False) + "\n")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > MAX_BUFFERED_PROMPTS:
            path.write_text(
                "\n".join(lines[-MAX_BUFFERED_PROMPTS:]) + "\n", encoding="utf-8"
            )
    except OSError:
        pass


def _prompts_from_buffer(session_id: str) -> list[str]:
    path = _buf_path(session_id)
    if not path.is_file():
        return []
    out: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            p = obj.get("p") if isinstance(obj, dict) else None
            if isinstance(p, str) and p.strip():
                out.append(p.strip())
    except OSError:
        return []
    return out


def clear_buffer(session_id: str) -> None:
    path = _buf_path(session_id)
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass


def set_current_session(session_id: str) -> None:
    if not session_id:
        return
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    try:
        (MEMORY_DIR / ".current_session").write_text(
            json.dumps(
                {
                    "session_id": session_id,
                    "sid": _short_sid(session_id),
                    "day": _today(),
                }
            ),
            encoding="utf-8",
        )
    except OSError:
        pass


def get_current_session_id() -> str:
    path = MEMORY_DIR / ".current_session"
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            sid = str(data.get("session_id") or "")
            if sid:
                return sid
        except (json.JSONDecodeError, OSError):
            pass
    return ""


def _parse_hot_sections(content: str) -> list[tuple[str, list[str]]]:
    sections: list[tuple[str, list[str]]] = []
    current_title: str | None = None
    current_bullets: list[str] = []
    for line in content.splitlines():
        m = TOPIC_HEADER_RE.match(line)
        if m:
            if current_title is not None:
                sections.append((current_title, current_bullets))
            current_title = m.group(1).strip()
            current_bullets = []
            continue
        if current_title is not None:
            if line.strip().startswith("- "):
                current_bullets.append(line.rstrip())
            elif not line.strip():
                continue
            else:
                current_bullets.append(line.rstrip())
    if current_title is not None:
        sections.append((current_title, current_bullets))
    return sections


def _render_hot(sections: list[tuple[str, list[str]]]) -> str:
    parts: list[str] = []
    for title, bullets in sections:
        if not bullets:
            continue
        parts.append(f"## {title}")
        parts.append("")
        for b in bullets:
            parts.append(b)
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def _section_matches_slug(title: str, slug: str) -> bool:
    if slugify(title) == slug:
        return True
    left = title.split("→")[0].split("->")[0].strip()
    return slugify(left) == slug


def upsert_hot_topic(
    slug: str,
    title: str,
    note: str,
    *,
    with_detail: bool,
) -> tuple[str, str]:
    """Upsert today's bullet under the topic section. Returns (action, hot_bullet)."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    day = _today()
    summary = (
        note
        if len(note) <= MAX_HOT_NOTE_CHARS
        else note[: MAX_HOT_NOTE_CHARS - 1].rstrip() + "…"
    )
    pointer = f" → hot-detail.md#{slug}" if with_detail else ""
    new_bullet = f"- [{day}] {summary}{pointer}"
    if len(new_bullet) > MAX_LINE_CHARS:
        if pointer and " → " in new_bullet:
            core, ptr = new_bullet.rsplit(" → ", 1)
            budget = MAX_LINE_CHARS - len(ptr) - 5
            new_bullet = core[: max(40, budget)].rstrip() + "… → " + ptr
        else:
            new_bullet = new_bullet[: MAX_LINE_CHARS - 1].rstrip() + "…"

    try:
        content = (
            HOT_PATH.read_text(encoding="utf-8", errors="replace")
            if HOT_PATH.exists()
            else ""
        )
    except OSError:
        content = ""

    sections = _parse_hot_sections(content)
    cleaned: list[tuple[str, list[str]]] = []
    for t, bullets in sections:
        kept = [b for b in bullets if not AUTO_TAG_RE.search(b)]
        if kept or not DATE_HEADER_RE.match(f"## {t}"):
            cleaned.append((t, kept))
    sections = [(t, b) for t, b in cleaned if b or not DATE_HEADER_RE.match(f"## {t}")]

    found_idx: int | None = None
    for i, (t, _) in enumerate(sections):
        if _section_matches_slug(t, slug):
            found_idx = i
            break

    if found_idx is None:
        sections = [(title, [new_bullet])] + sections
        action = "appended"
    else:
        t, bullets = sections[found_idx]
        display = t if len(t) >= len(title) else title
        new_bullets: list[str] = []
        replaced = False
        for b in bullets:
            bm = BULLET_DATE_RE.match(b.strip())
            if bm and bm.group(1) == day:
                if not replaced:
                    new_bullets.append(new_bullet)
                    replaced = True
                continue
            new_bullets.append(b)
        if not replaced:
            new_bullets = [new_bullet] + new_bullets
        sections[found_idx] = (display, new_bullets)
        active = sections.pop(found_idx)
        sections = [active] + sections
        action = "updated"

    HOT_PATH.write_text(_render_hot(sections), encoding="utf-8")
    return action, new_bullet


def _strip_legacy_auto_detail(content: str) -> str:
    """Remove ## YYYY-MM-DD-auto-<sid> blocks (session-era detail)."""
    lines = content.splitlines()
    kept: list[str] = []
    i = 0
    while i < len(lines):
        if LEGACY_DETAIL_ANCHOR_RE.match(lines[i]):
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                i += 1
            continue
        kept.append(lines[i])
        i += 1
    return "\n".join(kept).rstrip() + ("\n" if kept else "")


def upsert_hot_detail(slug: str, title: str, note: str, extra: dict | None = None) -> str:
    """Prepend a dated entry under ## <slug> in hot-detail.md."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    day = _today()
    hm = _now_hm()
    entry_lines = [
        f"- [{day} {hm}] {note}",
    ]
    if extra:
        for key in ("Done", "Remaining", "Files", "Open", "Context", "Approach", "Task"):
            val = extra.get(key) or extra.get(key.lower())
            if val:
                entry_lines.append(f"  - **{key}:** {val}")

    try:
        content = (
            HOT_DETAIL_PATH.read_text(encoding="utf-8", errors="replace")
            if HOT_DETAIL_PATH.exists()
            else ""
        )
    except OSError:
        content = ""

    content = _strip_legacy_auto_detail(content)
    lines = content.splitlines()

    # Find existing ## slug block
    start = None
    end = None
    for i, line in enumerate(lines):
        m = TOPIC_HEADER_RE.match(line)
        if m and slugify(m.group(1)) == slug:
            start = i
            j = i + 1
            while j < len(lines) and not lines[j].startswith("## "):
                j += 1
            end = j
            break

    block_body = entry_lines
    if start is not None and end is not None:
        old_body = lines[start + 1 : end]
        # drop blank lead
        while old_body and not old_body[0].strip():
            old_body = old_body[1:]
        new_block = [f"## {slug}", ""] + block_body + [""] + old_body
        rebuilt = lines[:start] + new_block + lines[end:]
        action = "updated"
    else:
        new_block = [f"## {slug}", ""] + block_body + [""]
        # strip leading blanks
        while lines and not lines[0].strip():
            lines = lines[1:]
        rebuilt = new_block + lines
        action = "appended"

    # collapse excessive blanks
    out: list[str] = []
    blank = 0
    for line in rebuilt:
        if not line.strip():
            blank += 1
            if blank <= 1:
                out.append("")
        else:
            blank = 0
            out.append(line)

    HOT_DETAIL_PATH.write_text("\n".join(out).rstrip() + "\n", encoding="utf-8")
    return action


def add_note(
    topic: str,
    note: str,
    *,
    title: str | None = None,
    detail: bool = True,
    extra: dict | None = None,
) -> dict:
    """Write a judgment jot under a topic. Returns {action, hot_line, anchor, slug}."""
    note = " ".join((note or "").split()).strip()
    if not note:
        return {"error": "empty note"}
    slug = slugify(topic)
    display = (title or "").strip() or (
        MISC_TITLE if slug == MISC_SLUG else title_from_slug(slug)
    )
    # Prefer a longer human title when topic looks like a display name
    if title is None and topic and slugify(topic) == slug and " " in topic.strip():
        display = topic.strip()

    with_detail = bool(detail or extra)
    action, hot_line = upsert_hot_topic(slug, display, note, with_detail=with_detail)
    detail_action = ""
    if with_detail:
        detail_action = upsert_hot_detail(slug, display, note, extra=extra)

    return {
        "action": action,
        "detail_action": detail_action,
        "hot_line": hot_line,
        "anchor": slug if with_detail else "",
        "slug": slug,
        "topic": display,
    }


def _content_to_text(content) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "text" and block.get("text"):
                    parts.append(str(block["text"]))
                elif "text" in block:
                    parts.append(str(block["text"]))
        return " ".join(parts).strip()
    if isinstance(content, dict) and "text" in content:
        return str(content["text"]).strip()
    return ""


def _prompts_from_transcript(path: Path) -> list[str]:
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    found: list[str] = []
    for line in raw.splitlines()[-200:]:
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        role = (obj.get("role") or obj.get("type") or "").lower()
        content = obj.get("content") or obj.get("text")
        msg = obj.get("message")
        if isinstance(msg, dict):
            role = (msg.get("role") or role).lower()
            content = msg.get("content", content)
        if role not in ("user", "human"):
            continue
        text = _content_to_text(content)
        if text:
            found.append(text)
    return found[-12:]


def _prompts_from_payload(payload: dict) -> list[str]:
    prompts: list[str] = []
    for p in payload.get("prompts") or []:
        if isinstance(p, str) and p.strip():
            prompts.append(p.strip())
    for key in ("prompt", "last_prompt", "user_message"):
        v = payload.get(key)
        if isinstance(v, str) and v.strip():
            prompts.append(v.strip())
    tpath = payload.get("transcript_path") or payload.get("transcriptPath")
    if tpath and Path(str(tpath)).is_file():
        prompts.extend(_prompts_from_transcript(Path(str(tpath))))
    sid = str(
        payload.get("session_id")
        or payload.get("sessionId")
        or payload.get("sessionID")
        or ""
    )
    if sid:
        for p in _prompts_from_buffer(sid):
            if p not in prompts:
                prompts.append(p)
    return prompts


def main() -> int:
    # Buffer only — no hot write
    if len(sys.argv) > 1 and sys.argv[1] == "--buffer":
        try:
            payload = json.load(sys.stdin)
        except Exception:
            return 0
        if isinstance(payload, dict):
            sid = str(
                payload.get("session_id")
                or payload.get("sessionId")
                or payload.get("sessionID")
                or ""
            )
            prompt = str(payload.get("prompt") or payload.get("user_message") or "")
            append_prompt(sid, prompt)
            if sid:
                set_current_session(sid)
        return 0

    # Judgment jot: topic + note
    if len(sys.argv) > 1 and sys.argv[1] == "--note":
        try:
            payload = json.load(sys.stdin)
        except Exception:
            return 0
        if not isinstance(payload, dict):
            return 0
        note = str(
            payload.get("note") or payload.get("text") or payload.get("prompt") or ""
        )
        topic = str(
            payload.get("topic")
            or payload.get("slug")
            or payload.get("title")
            or MISC_SLUG
        )
        title = payload.get("title")
        title_s = str(title).strip() if title else None
        detail = payload.get("detail")
        with_detail = True if detail is None else bool(detail)
        extra = payload.get("extra") if isinstance(payload.get("extra"), dict) else None
        result = add_note(topic, note, title=title_s, detail=with_detail, extra=extra)
        sid = str(
            payload.get("session_id")
            or payload.get("sessionId")
            or payload.get("sessionID")
            or get_current_session_id()
            or ""
        )
        if sid:
            set_current_session(sid)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if "error" not in result else 1

    # Default: auto hook path — buffer only, never write hot
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    if not isinstance(payload, dict):
        return 0

    session_id = str(
        payload.get("session_id")
        or payload.get("sessionId")
        or payload.get("sessionID")
        or ""
    )
    reason = str(payload.get("reason") or payload.get("type") or "").strip().lower()

    # Absorb any prompts into buffer
    prompts = _prompts_from_payload(payload)
    if session_id:
        set_current_session(session_id)
        for p in prompts:
            # Avoid re-duplicating full buffer dump — only append last if payload
            # brought a single new prompt; for list payloads, rewrite buffer once
            pass
        # If payload carried prompts explicitly, refresh buffer from them
        if payload.get("prompts") or payload.get("prompt") or payload.get("user_message"):
            path = _buf_path(session_id)
            try:
                PROMPT_BUF_DIR.mkdir(parents=True, exist_ok=True)
                cleaned = []
                seen: set[str] = set()
                for p in prompts:
                    t = " ".join(p.split()).strip()
                    if not t:
                        continue
                    key = t[:60].lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    cleaned.append(t)
                cleaned = cleaned[-MAX_BUFFERED_PROMPTS:]
                path.write_text(
                    "\n".join(
                        json.dumps({"t": _now_hm(), "p": p}, ensure_ascii=False)
                        for p in cleaned
                    )
                    + ("\n" if cleaned else ""),
                    encoding="utf-8",
                )
            except OSError:
                pass

    if reason in ("clear", "logout", "deleted", "prompt_input_exit", "other") and session_id:
        clear_buffer(session_id)

    if os.environ.get("MIA_PLUGIN_DEBUG") or os.environ.get("MIA_CAPTURE_DEBUG"):
        print(
            f"session_capture buffer-only sid={_short_sid(session_id)} "
            f"reason={reason} prompts={len(prompts)}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())