"""Hybrid search index for dobby's knowledge layer.

Builds a lightweight BM25 inverted index over all .md files in knowledge/,
stores file mtimes for recency weighting, and records [[wikilink]] adjacency
for 1-hop graph expansion. Query path fuses recency-weighted BM25 with the
graph list via Reciprocal Rank Fusion (RRF).

memory/ is NOT indexed — hot.md is always in context (injected at session start)
and noteworthy items get promoted to knowledge/ before expiring.

Called at session start to refresh the index, and on-demand by
knowledge_lookup.py to score prompts against the corpus.

Usage:
    # Build/refresh index (session start):
    python hooks/bm25_index.py --build

    # Query (returns JSON list of {path, score, snippet}):
    echo "call volume trends" | python hooks/bm25_index.py --query --top 5

    # Compile check:
    python -m py_compile hooks/bm25_index.py

Index is stored at memory/.search_index.json. Rebuilds in <100ms for ~200 files.
Zero external dependencies — uses only Python stdlib.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from pathlib import Path
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).parent.parent
KNOWLEDGE_DIR = ROOT / "knowledge"
INDEX_PATH = ROOT / "memory" / ".search_index.json"

# Directories and files to skip during indexing.
SKIP_DIRS = {".obsidian", ".claude", ".claudian", ".playwright-mcp", "cas", "naic", "query_examples", "__pycache__"}
SKIP_FILES = {".gitkeep", ".search_index.json"}
SKIP_EXTENSIONS = {".pdf", ".pyc", ".json", ".url.md"}  # .url.md stubs are just links

# Frontmatter pattern
FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)

# Wikilink pattern — captures target before any | display text
WIKILINK_RE = re.compile(r"\[\[([^\]|]+)")

# Tokenization: split on non-alphanumeric, lowercase, drop short tokens
TOKEN_RE = re.compile(r"[a-zA-Z0-9_]+")
STOP_WORDS = frozenset({
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "this", "that", "these", "those",
    "it", "its", "not", "no", "if", "then", "else", "when", "where",
    "how", "what", "which", "who", "whom", "why", "all", "each", "every",
    "any", "some", "such", "than", "too", "very", "just", "also", "as",
    "so", "up", "out", "about", "into", "over", "after", "before",
    "between", "under", "above", "below", "use", "used", "using",
})

# BM25 parameters
K1 = 1.5
B = 0.75

# Recency: half-life in days. Score multiplier = 0.5^(age/half_life).
# Gentle for a personal vault — a fact's age says little about its relevance
# (last year's allergy, your car's specs, a friend's kids' names are all still true).
# ~1.0 for brand-new, ~0.5 at 180d, ~0.71 at 90d. Recency still floats what you're
# actively touching without burying durable personal facts.
RECENCY_HALF_LIFE_DAYS = 180.0

# Reciprocal Rank Fusion constant (standard Cormack et al. value).
RRF_K = 60

# Index schema version — bump when doc fields change so stale caches rebuild.
INDEX_VERSION = 2


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase terms, dropping stop words and short tokens."""
    return [
        t.lower() for t in TOKEN_RE.findall(text)
        if len(t) >= 2 and t.lower() not in STOP_WORDS
    ]


def extract_searchable_text(path: Path) -> str:
    """Extract text for indexing: filename + frontmatter fields + first ~2000 chars of body."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""

    parts: list[str] = []

    # Filename is highly relevant (e.g. "InsuranceDM.Fact_PolicyPremium")
    stem = path.stem.replace(".", " ").replace("-", " ").replace("_", " ")
    parts.append(stem)
    # Boost filename by repeating it
    parts.append(stem)

    # Extract frontmatter fields that aid retrieval
    fm = FRONTMATTER_RE.match(raw)
    if fm:
        for line in fm.group(1).splitlines():
            line_stripped = line.strip()
            for field in ("triggers:", "tags:", "aliases:", "title:", "table:", "schema:", "type:", "domain:"):
                if line_stripped.startswith(field):
                    val = line_stripped.split(":", 1)[1].strip().strip("[]\"'")
                    parts.append(val)
        body = raw[fm.end():]
    else:
        body = raw

    # First ~2000 chars of body (covers key sections without bloating index)
    parts.append(body[:2000])

    return " ".join(parts)


def extract_wikilinks(path: Path, stem_to_path: dict[str, str], self_path: str) -> list[str]:
    """Return resolved rel_paths for all [[wikilinks]] in a file (outbound, deduplicated)."""
    try:
        raw = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    seen: set[str] = set()
    result: list[str] = []
    for m in WIKILINK_RE.finditer(raw):
        stem = m.group(1).strip()
        target = stem_to_path.get(stem)
        if target and target != self_path and target not in seen:
            seen.add(target)
            result.append(target)
    return result


def scan_files() -> list[Path]:
    """Find all indexable .md files in knowledge/."""
    files: list[Path] = []

    if not KNOWLEDGE_DIR.exists():
        return files

    for path in sorted(KNOWLEDGE_DIR.rglob("*.md")):
        # Skip excluded directories
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        # Skip excluded files
        if path.name in SKIP_FILES:
            continue
        # Skip non-md extensions that match .md glob (e.g. .url.md)
        if any(path.name.endswith(ext) for ext in SKIP_EXTENSIONS):
            continue
        files.append(path)

    return files


def build_index() -> dict:
    """Build BM25 index over all knowledge/ and memory/ .md files."""
    files = scan_files()

    # Build stem→rel_path map for wikilink resolution before filtering
    stem_to_path: dict[str, str] = {
        path.stem: str(path.relative_to(ROOT)).replace("\\", "/")
        for path in files
    }

    df: Counter = Counter()
    docs: list[dict] = []
    links: dict[str, list[str]] = {}
    total_len = 0

    for path in files:
        text = extract_searchable_text(path)
        tokens = tokenize(text)
        if not tokens:
            continue

        tf = Counter(tokens)
        rel_path = str(path.relative_to(ROOT)).replace("\\", "/")
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0.0

        docs.append({
            "path": rel_path,
            "tf": dict(tf),
            "len": len(tokens),
            "snippet": text[:200].replace("\n", " ").strip(),
            "mtime": mtime,
        })
        total_len += len(tokens)

        for term in set(tokens):
            df[term] += 1

        outbound = extract_wikilinks(path, stem_to_path, rel_path)
        if outbound:
            links[rel_path] = outbound

    avg_dl = total_len / max(len(docs), 1)

    return {
        "version": INDEX_VERSION,
        "num_docs": len(docs),
        "avg_dl": avg_dl,
        "df": dict(df),
        "docs": docs,
        "links": links,
    }


def save_index(index: dict) -> None:
    """Save index to memory/.search_index.json."""
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")


def load_index() -> dict | None:
    """Load index from disk. Returns None if not found or schema is stale."""
    if not INDEX_PATH.exists():
        return None
    try:
        index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    if index.get("version", 1) < INDEX_VERSION:
        return None
    return index


def recency_factor(mtime: float, now: float | None = None) -> float:
    """Half-life decay on file mtime. Missing/zero mtime → 1.0 (no penalty)."""
    if not mtime:
        return 1.0
    if now is None:
        now = __import__("time").time()
    age_days = max(0.0, (now - mtime) / 86400.0)
    return math.exp(-math.log(2.0) * age_days / RECENCY_HALF_LIFE_DAYS)


def bm25_score(
    query_tokens: list[str],
    index: dict,
    *,
    apply_recency: bool = True,
    now: float | None = None,
) -> list[dict]:
    """Score all documents against query tokens using BM25 (± recency). Sorted desc."""
    df = index["df"]
    n = index["num_docs"]
    avg_dl = index["avg_dl"]
    if now is None:
        now = __import__("time").time()

    results: list[dict] = []

    for doc in index["docs"]:
        score = 0.0
        dl = doc["len"]
        tf_map = doc["tf"]

        for term in query_tokens:
            if term not in tf_map:
                continue
            tf_val = tf_map[term]
            df_val = df.get(term, 0)
            if df_val == 0:
                continue

            # IDF component
            idf = math.log((n - df_val + 0.5) / (df_val + 0.5) + 1.0)
            # TF component with length normalization
            tf_norm = (tf_val * (K1 + 1)) / (tf_val + K1 * (1 - B + B * dl / avg_dl))
            score += idf * tf_norm

        if score <= 0:
            continue

        mtime = float(doc.get("mtime") or 0.0)
        if apply_recency:
            score *= recency_factor(mtime, now)

        results.append({
            "path": doc["path"],
            "score": round(score, 4),
            "bm25": round(score, 4),  # post-recency lexical score (pre-RRF)
            "snippet": doc["snippet"],
            "mtime": mtime,
        })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results


def rrf_fuse(
    ranked_lists: list[list[dict]],
    *,
    k: int = RRF_K,
) -> list[dict]:
    """Reciprocal Rank Fusion over ranked result lists (each item needs 'path').

    RRF score for a path = Σ 1/(k + rank_i) across lists that contain it.
    Preserves best snippet/mtime/via metadata from the first list that had the path.
    """
    scores: dict[str, float] = {}
    meta: dict[str, dict] = {}

    for ranked in ranked_lists:
        for rank, item in enumerate(ranked, start=1):
            path = item.get("path")
            if not path:
                continue
            scores[path] = scores.get(path, 0.0) + 1.0 / (k + rank)
            if path not in meta:
                meta[path] = dict(item)

    fused: list[dict] = []
    for path, rrf in scores.items():
        row = meta[path]
        row = {
            **row,
            "path": path,
            "score": round(rrf, 6),
            "rrf": round(rrf, 6),
        }
        fused.append(row)

    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused


def graph_neighbor_list(
    seed_hits: list[dict],
    index: dict,
    *,
    decay: float = 0.6,
    min_seed_score: float = 0.0,
) -> list[dict]:
    """Build a ranked list of 1-hop wikilink neighbors from seed BM25 hits.

    Neighbor priority = parent_score × decay (higher parent → higher neighbor rank).
    """
    links = index.get("links") or {}
    if not links:
        return []

    best: dict[str, dict] = {}
    for hit in seed_hits:
        parent_score = float(hit.get("score") or 0.0)
        if parent_score < min_seed_score:
            continue
        parent_path = hit["path"]
        parent_label = parent_path.split("/")[-1].replace(".md", "")
        neighbor_score = parent_score * decay
        for linked_path in links.get(parent_path, []):
            if linked_path == parent_path:
                continue
            prev = best.get(linked_path)
            if prev is None or neighbor_score > float(prev.get("score") or 0.0):
                best[linked_path] = {
                    "path": linked_path,
                    "score": round(neighbor_score, 4),
                    "via": parent_label,
                }

    return sorted(best.values(), key=lambda x: x["score"], reverse=True)


def hybrid_retrieve(
    query_tokens: list[str],
    index: dict,
    *,
    top_n: int = 5,
    min_score: float = 4.0,
    graph_decay: float = 0.6,
    now: float | None = None,
) -> list[dict]:
    """Hybrid ranker: recency-weighted BM25 + 1-hop graph, fused with RRF.

    1. BM25 × recency (half-life RECENCY_HALF_LIFE_DAYS)
    2. Keep lexical survivors with score >= min_score
    3. Build graph-neighbor list from those seeds
    4. RRF fuse the two ranked lists; return top_n
    """
    lexical = bm25_score(query_tokens, index, apply_recency=True, now=now)
    seeds = [r for r in lexical if r["score"] >= min_score]
    if not seeds:
        return []

    neighbors = graph_neighbor_list(
        seeds, index, decay=graph_decay, min_seed_score=min_score
    )

    # RRF over survivors only — graph list may be empty (then RRF ≈ lexical order).
    fused = rrf_fuse([seeds, neighbors] if neighbors else [seeds])
    return fused[:top_n]


def main() -> None:
    args = sys.argv[1:]

    if "--build" in args:
        index = build_index()
        save_index(index)
        # Print nothing on success — used as a SessionStart hook
        return

    if "--query" in args:
        # Read query from stdin
        try:
            query_text = sys.stdin.read().strip()
        except Exception:
            return
        if not query_text:
            return

        index = load_index()
        if index is None:
            # Auto-build if missing
            index = build_index()
            save_index(index)

        query_tokens = tokenize(query_text)
        if not query_tokens:
            return

        top_n = 5
        for i, arg in enumerate(args):
            if arg == "--top" and i + 1 < len(args):
                try:
                    top_n = int(args[i + 1])
                except ValueError:
                    pass

        # CLI default: hybrid (recency BM25 + graph RRF). Pass --lexical for plain BM25.
        if "--lexical" in args:
            results = bm25_score(query_tokens, index)[:top_n]
        else:
            results = hybrid_retrieve(query_tokens, index, top_n=top_n, min_score=0.0)
        print(json.dumps(results, indent=2))
        return

    # Default: print usage
    print(
        "Usage: python bm25_index.py --build | --query [--top N] [--lexical]",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()