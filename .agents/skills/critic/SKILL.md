---
name: critic
description: Tear apart a finished piece of work with fresh, adversarial eyes before it ships. Use on any significant output — a draft, an analysis, a plan you've already built, a decision, a piece of code. Triggers on "critique this", "poke holes in this", "red-team this", "tear this apart", "what's wrong with this", "review this hard", "/critic".
argument-hint: "[paste or point to the output to critique]"
---

# critic

A fresh set of eyes on finished work. The whole value is **independence** — reviewing something as if you did not write it. Assume the author is competent and the numbers may be right; your job is to find where it's *wrong, weak, or fooling itself*, not to praise it.

Sibling skill: `grilling` stress-tests **plans before you build**; `critic` stress-tests **output after you build**.

## Independence is the whole point — spawn, don't self-review

If you (the main assistant) wrote the thing being critiqued, **do not critique it in this same thread** — you'll anchor on your own reasoning and rubber-stamp it, which is exactly the failure this skill exists to prevent. Instead **spawn a fresh-context Task worker** and hand it *only* the artifact + its claim (no history of how you built it). Let the worker return the findings block below; then you act on it.

Critique in-thread only when the work under review was written by *someone else* (the user pasted a draft, another tool produced output) — there, this thread already is the fresh set of eyes.

---

## How to run it

1. **Identify the artifact and its claim.** What is this output asserting or recommending? What would "correct" mean? If it's ambiguous, state the interpretation you're reviewing against.

2. **Attack along these axes** — spend effort where the work is most load-bearing:
   - **Correctness** — Is anything factually wrong, miscalculated, or internally contradictory? Do the numbers reconcile? Trace at least one key figure back to its source.
   - **Weakest assumption** — What single assumption, if false, collapses the conclusion? How likely is it false?
   - **Alternative reading** — Give a plausible different interpretation of the same evidence.
   - **Omissions** — What did the work ignore — a counterexample, a cohort, a cost, a failure mode, a stakeholder?
   - **Overreach** — Where does the confidence exceed the evidence? Flag hedge-free claims that should be hedged.
   - **Clarity/fitness** — For writing: does it actually land for its audience? For code: edge cases, failure handling, correctness under load?

3. **Verdict.** For each major claim, rate it **robust / uncertain / fragile** and say why in one line.

4. **Fixes.** For every fragile or uncertain item, give the concrete change that would fix it — not just "reconsider X."

---

## Output shape

```
## Critique: [what's being reviewed]

**Bottom line:** [ship it / fix these first / rethink] — one sentence.

### Findings
1. [axis] — [the problem] → [verdict: robust/uncertain/fragile] → [fix]
2. ...

### Weakest link
[the one thing most likely to be wrong, and what to do about it]
```

---

## Rules

- Be genuinely critical. Agreement without grounds is useless — if it's actually solid, say so briefly and stop, but look hard first.
- One pushback per point, with reasoning — don't nag.
- Don't rewrite the whole thing; point precisely and prescribe the fix.
- If you need to verify a claim, verify it (read the file, run the check) rather than speculating.
- When invoked as a fan-out worker inside a larger task, review only the artifact handed to you and return the findings block.