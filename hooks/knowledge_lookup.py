"""UserPromptSubmit hook — inject relevant knowledge for the current prompt.

Hybrid retrieval (recency-weighted BM25 + 1-hop wikilink graph, RRF-fused)
selects top hits; short excerpts are injected as invisible internal context.
The model answers from the material; no path catalogs or score lists.

Cost: ~50-100 tokens of metadata + up to ~2500 chars of excerpts when matches
are found. Zero when no match.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# Prefer DOBBY_HOME (plugin / multi-client); fall back to repo relative to this file.
_dobby = os.environ.get("DOBBY_HOME", "").strip()
ROOT = Path(_dobby) if _dobby and Path(_dobby).is_dir() else Path(__file__).parent.parent

# Minimum BM25 score to surface a pointer. Below this, results are noise.
MIN_SCORE = 4.0

# Maximum number of pointers to show per prompt.
MAX_POINTERS = 5

# Auto-include short excerpts so models don't stop at the path list.
# Top N direct hits (not link-expanded-only) get a capped excerpt.
EXCERPT_TOP_N = 2
EXCERPT_CHARS = 1200  # per file
MAX_TOTAL_EXCERPT_CHARS = 2500


_MODE_DESCRIPTIONS = {
    "ludicrous": "Maximum brevity. No preamble, hedging, or softening. Answer only. 10 words max.",
    "savage": "No filter, no mercy, no reason needed. Mock the question AND the asker. Find something to needle even in a perfectly reasonable request. Answer is correct and complete, delivered with maximum disdain.",
    "intern": "Boundless enthusiasm, slightly incomplete knowledge. Offer to make a deck. Use 'circle back' without irony.",
    "legal": "Never commit. Hedge everything with ASOP citations. Verbose by design. Cc everyone.",
    "shakespeare": "Archaic English — thee/thou/hath/doth. Actuarial terms in iambic phrasing. Every analysis is a soliloquy.",
    "plaid": "Bullet points only. No prose. No full sentences. Every item is an action or a question.",
    "chill": "Therapist energy. Nothing is a crisis. Ends with an open question. Never says 'urgent.'",
    "consultant": "Three levers. Strategic frameworks. Scope creep is a feature. 'Socialize' and 'ideation' are verbs.",
    "noir": "Hard-boiled first-person narration. The data always has something to hide. World-weary but correct.",
    "actuary": "Technically correct answer to a slightly different question. So many caveats the answer is nearly unusable.",
    "gen alpha": "Internet brainrot. No cap fr fr, rizz, lowkey, slay, bussin, W/L energy, delulu, bestie. All lowercase. Correct analysis, completely unhinged delivery.",
    "spongebob": "Rotate between Spongebob (enthusiasm), Patrick (confident wrongness), Squidward (done with everything).",
}


def _inject_mode(session_id: str) -> None:
    tmp = Path(tempfile.gettempdir())
    # prefer session-scoped file; fall back to legacy global
    candidates = (
        [tmp / f"dobby_mode_{session_id}.json", tmp / "dobby_mode.json"]
        if session_id
        else [tmp / "dobby_mode.json"]
    )
    for mode_file in candidates:
        try:
            data = json.loads(mode_file.read_text(encoding="utf-8"))
            mode = data.get("mode", "")
            if not mode:
                continue
            desc = _MODE_DESCRIPTIONS.get(mode, "")
            suffix = f" — {desc}" if desc else ""
            print(f"[ACTIVE MODE: {mode}{suffix}] Maintain this voice for your entire response.")
            return
        except Exception:
            continue


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return

    session_id = payload.get("session_id", "")
    _inject_mode(session_id)

    prompt = (payload.get("prompt") or "").strip()
    if not prompt:
        return

    # Buffer prompt for frequent auto-capture (Claude Stop has no prompt list).
    try:
        capture_path = ROOT / "hooks" / "session_capture.py"
        if capture_path.is_file() and session_id:
            spec_c = importlib.util.spec_from_file_location("session_capture", capture_path)
            capture = importlib.util.module_from_spec(spec_c)
            assert spec_c and spec_c.loader
            spec_c.loader.exec_module(capture)
            capture.append_prompt(str(session_id), prompt)
    except Exception:
        pass

    # Load BM25 module
    bm25_path = ROOT / "hooks" / "bm25_index.py"
    if not bm25_path.exists():
        return

    try:
        spec = importlib.util.spec_from_file_location("bm25_index", bm25_path)
        bm25 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bm25)

        index = bm25.load_index()
        if index is None:
            return

        tokens = bm25.tokenize(prompt)
        if not tokens:
            return

        # Hybrid: recency-weighted BM25 + 1-hop wikilink graph, RRF-fused.
        results = bm25.hybrid_retrieve(
            tokens,
            index,
            top_n=MAX_POINTERS + 2,
            min_score=MIN_SCORE,
        )
    except Exception:
        return

    if not results:
        return

    # Prefer substantive docs over hub indexes when both match.
    def _rank_key(r: dict) -> tuple:
        p = r.get("path", "")
        hub = 1 if p.endswith("_index.md") or "data-technology-policies" in p else 0
        return (hub, -float(r.get("score") or 0))

    results = sorted(results, key=_rank_key)
    direct = [r for r in results if not r.get("via")] or results

    # Load full-ish content for top hits — no path catalogs, no BM25 score lists.
    # Goal: model behaves like a colleague who already knows the material, not a RAG UI.
    excerpt_budget = MAX_TOTAL_EXCERPT_CHARS
    bodies: list[str] = []
    source_paths: list[str] = []
    for r in direct[:EXCERPT_TOP_N]:
        if excerpt_budget <= 200:
            break
        rel = r["path"]
        fpath = ROOT / rel
        if not fpath.is_file():
            alt = ROOT / "knowledge" / rel
            fpath = alt if alt.is_file() else fpath
        if not fpath.is_file():
            continue
        try:
            raw = fpath.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if raw.startswith("---"):
            parts = raw.split("---", 2)
            if len(parts) >= 3:
                raw = parts[2]
        cap = min(EXCERPT_CHARS, excerpt_budget)
        body = raw.strip()
        if len(body) > cap:
            body = body[:cap].rstrip() + "\n…"
        excerpt_budget -= len(body)
        bodies.append(body)
        source_paths.append(rel)

    if not bodies:
        return

    # Invisible retrieval: content only + brief behavioral constraint.
    lines = [
        "<internal-context>",
        "The following is background material already selected for this turn.",
        "Use it to answer the user the way a strong analyst would: clear, direct, "
        "synthesized. Do not describe your search process. Do not list knowledge "
        "files, scores, Primary/Adjacent maps, or 'start with X.md'. If sources "
        "matter, one short line at the end is enough.",
        "",
    ]
    for i, body in enumerate(bodies):
        lines.append(body)
        if i < len(bodies) - 1:
            lines.append("")
            lines.append("---")
            lines.append("")
    lines.append("</internal-context>")
    if source_paths:
        lines.append(f"<!-- sources: {', '.join(source_paths)} -->")

    print("\n".join(lines))


if __name__ == "__main__":
    main()