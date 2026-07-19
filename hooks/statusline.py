"""dobby statusline -- one-line status for the CLI status bar.

Outputs:
  dobby 😊                       (all good — face rotates randomly)
  dobby ⚡ [ludicrous mode activated]   (a personality mode is active)
  dobby 😊  sonnet               (with model label when discoverable)
"""
import json
import os
import random
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

MODE_FILE = Path(tempfile.gettempdir()) / "dobby_mode.json"

MODE_FACES = {
    "ludicrous": "⚡",
    "savage": "😈",
    "intern": "🤩",
    "legal": "⚖️",
    "shakespeare": "🎭",
    "plaid": "📋",
    "chill": "😌",
    "consultant": "💼",
    "noir": "🕵️",
    "actuary": "🧮",
    "gen alpha": "🫡",
    "spongebob": "🧽",
}

HAPPY_FACES = [
    "😊", "🙂", "😎", "🤓", "🧐", "😄", "😌", "🫡",  # calm / classic
    "🤩", "🥳", "😁", "🤗", "😃",                       # energetic
    "🤪", "😜", "😝", "😏", "🤠", "😈", "🥸",           # fun / chaotic
    "🤯", "🤖", "🫠", "🥹",                        # unhinged / geeky
]


def _read_mode() -> str:
    tmp = Path(tempfile.gettempdir())
    session_id = os.environ.get("CLAUDE_CODE_SESSION_ID", "") or os.environ.get(
        "OPENCODE_SESSION_ID", ""
    )
    if session_id:
        session_file = tmp / f"dobby_mode_{session_id}.json"
        if session_file.exists():
            try:
                return json.loads(session_file.read_text(encoding="utf-8")).get("mode", "")
            except Exception:
                return ""
        return ""
    # fallback: no session ID — pick most-recently-written file
    candidates = sorted(
        [*tmp.glob("dobby_mode_*.json"), tmp / "dobby_mode.json"],
        key=lambda p: p.stat().st_mtime if p.exists() else 0,
        reverse=True,
    )
    for path in candidates:
        try:
            mode = json.loads(path.read_text(encoding="utf-8")).get("mode", "")
            if mode:
                return mode
        except Exception:
            continue
    return ""


def _current_model() -> str:
    for path in (
        Path.home() / ".config" / "opencode" / "opencode.jsonc",
        Path.home() / ".claude" / "settings.json",
    ):
        try:
            raw = path.read_text(encoding="utf-8")
            # tolerate // comments in jsonc
            raw = "\n".join(l for l in raw.splitlines() if not l.strip().startswith("//"))
            model = json.loads(raw).get("model", "")
            if model:
                return model
        except Exception:
            continue
    return os.environ.get("ANTHROPIC_MODEL", "")


def _model_label(model: str) -> str:
    if not model:
        return ""
    tail = model.split("/")[-1]
    parts = tail.split("-")
    # claude-sonnet-4 -> sonnet ; gpt-4o -> gpt
    return parts[1] if parts[0] == "claude" and len(parts) > 1 else parts[0]


def main() -> None:
    mode = _read_mode()
    mode_face = MODE_FACES.get(mode) if mode else None
    mode_label = f" [{mode} mode activated]" if mode else ""
    face = mode_face if mode_face else random.choice(HAPPY_FACES)

    label = _model_label(_current_model())
    tail = f"  {label}" if label else ""
    print(f"dobby {face}{mode_label}{tail}")


if __name__ == "__main__":
    main()