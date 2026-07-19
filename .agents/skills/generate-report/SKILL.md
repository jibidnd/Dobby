---
name: generate-report
description: Generate a self-contained HTML report summarizing an investigation â€” context, method, figures, tables, findings. Use when the user asks for a "report", "writeup", "summary doc", or wants to hand off findings. Collaborate to clarify scope before writing.
argument-hint: "[report topic or scope]"
---

# generate-report

Produce a single self-contained `.html` file that answers the question at hand and is ready to hand off. Write for **the user** â€” their role, audience, and fluency are in `dobby.local.md`; match that level. Be **precise, factual, and analytical**: lead with the answer, support every claim with a value from the data, no fluff, and flag uncertainty honestly.

## Before writing

1. **Confirm scope** in 1â€“3 short questions if not obvious: the question, the audience (self / team / external), the time window. Skip if the brief is already tight.
2. **Inventory your inputs.** Findings can come from anywhere — a data file (CSV/Excel), a PDF, web research, or analysis already done this session. Use what you have; don't re-pull or re-read.
3. **Pick the figures** â€” the 2â€“5 plots/tables that actually answer the question. Resist decorative charts.
4. **Load dataviz conventions** â€” if the report includes any chart, stat tile, or styled table, read `@../dataviz-conventions.md` now. Every color, chart type, CSS rule, and matplotlib setting comes from there â€” no ad-hoc overrides.

## Grounding (non-negotiable)

Every directional or evaluative statement ("rising", "higher", "improved", "confirmed") must trace to a specific value in the data you actually have â€” a table cell, query result, or chart reading. Never assert a direction from expectation or by repeating an unchecked claim. If a chart reads flat or zero, say so. If a source can't be verified, say that rather than implying it.

## Output

- Path: `~/.claude/outputs/reports/<slug>_<YYYY-MM-DD>.html` (create the dir if missing). Never write outputs inside the dobby repo.
- Self-contained: inline CSS, base64-embed PNG figures (`matplotlib` â†’ `BytesIO` â†’ base64). No external assets.
- Plain HTML + minimal CSS. No frameworks; only a tiny `<details>`/`<summary>` for toggles.

## Structure

```
<h1> question / title
<p>  one-paragraph TL;DR (answer + headline number)
<h2> Context        â€” why this came up, who asked, what decision it informs
<h2> Data & method  â€” Data sources and definitions, assumptions, methodology, filters, caveats. Required: a "Sources" <details> block.
<h2> Findings       â€” narrative + figures. Each figure: caption, chart, then 1â€“2 sentence read
<h2> Diagnostics    â€” sensitivity, breakdowns, sanity checks. Default-collapsed <details>
<h2> Appendix       â€” full tables, definitions. Default-collapsed
```

Use `<details><summary>â€¦</summary>â€¦</details>` for anything long or secondary. `<h2>` headers with anchor IDs.

### Required: Sources block

Every report MUST include a collapsible block that makes each figure/table reproducible â€” list the source behind each one:

- pulled from the warehouse â†’ the **SQL query**;
- from a file â†’ the **path** + any transformation;
- from prior in-session work â†’ a one-line note of how it was produced.

The point: every number is auditable from the report alone. Don't omit a source because it was "small."

## Style

- Numbers: thousands separators, % to 1 decimal, currency to nearest unit unless precision matters.
- Tables and figures: see `@../dataviz-conventions.md` â€” CSS, rcParams, and chart types are defined there.
- Codes / identifiers (versions, IDs, keys): preserve verbatim.

## After writing

1. State the report's path and the headline finding in one sentence. Don't re-summarize â€” the user can open it.
2. **Ask whether to save the build script** (the code that produced the report) via `AskUserQuestion`:
   - **Save** â†’ `~/.claude/outputs/reports/scripts/<slug>_<YYYY-MM-DD>.py` so it can be re-run / tweaked / versioned.
   - **Discard** â†’ delete the temp script.

   The script is what makes the report reproducible â€” the user often wants it.

3. **Update memory** (non-negotiable â€” do this every time):
   - Invoke `/jot` to capture what was built and the headline finding.