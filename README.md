# jev-openrouter-example

A minimal, dependency-free example of calling TypeSafe's **Jev** model through
**OpenRouter's Decisions API** — one script, one request, three typed decisions.

## What is Jev?

Jev ([typesafe.ai](https://typesafe.ai)) is TypeSafe AI's first "System One"
model. It is not a chat model: it generates no text. You send it a `state`
plus typed questions, and it returns calibrated probabilities your code can
branch on directly:

| Question type | Returns |
|---|---|
| `noul` | P(yes) as a float 0..1 |
| `choice` | winning key + per-option probabilities + confidence |
| `score` | position on your ordered rubric (can be fractional) + per-level probabilities |

Typical uses: routing, classification, guardrail checks, grading output against
a rubric — anywhere a fast, cheap semantic judgment beats a full LLM round-trip.

## The API

Jev on OpenRouter runs on the **Decisions API**, not chat completions:

```
POST https://openrouter.ai/api/alpha/decisions
```

Request body: `{ "model": "typesafe/jev-1.13", "state": ..., "questions": { ... } }`.
Chat-completions SDKs will not work with it. Pricing: **$0.042 / 1M input
tokens, output free**. Each call in the example below cost about $0.000018.

## Run it

```bash
export OPENROUTER_API_KEY="your-openrouter-key"   # from https://openrouter.ai/keys
python3 jev_example.py
```

No dependencies — stdlib only. Python 3.8+.

## What the example does

`jev_example.py` sends two support tickets through a single request each,
asking all three question types in parallel:

- `urgent` (noul): does the ticket express urgency?
- `team` (choice): which team owns it — billing, technical, or sales?
- `frustration` (score): how frustrated is the customer — Calm / Concerned but civil / Very angry?

Sample output from a real run (2026-09-19):

```
State: The payment integration has failed for three days straight. Every retry
charges us twice and support has gone silent. Fix this TODAY or we are moving
to a competitor.

=== Angry ticket (917 ms round-trip) ===
  [urgent] noul  -> P(yes) = 0.990
  [team] choice -> technical (confidence 0.560)
           probs: billing=0.290, sales=0.000, technical=0.710
  [frustration] score  -> 2 (Very angry), confidence 1.000
           probs: 0=0.000, 1=0.000, 2=1.000
  usage: 423 in / 70 out | cost $0.000018 | served by TypeSafe (typesafe/jev-1.13-20260917)

State: Hi, quick question about our invoice from last month -- the line item for
add-on seats looks higher than we expected. No rush, just want to understand it
when you get a chance.

=== Calm ticket (599 ms round-trip) ===
  [urgent] noul  -> P(yes) = 0.060
  [team] choice -> billing (confidence 0.990)
           probs: billing=1.000, technical=0.000, sales=0.000
  [frustration] score  -> 0.69 (0.69), confidence 0.540
           probs: 0=0.310, 1=0.690, 2=0.000
  usage: 429 in / 70 out | cost $0.000018 | served by TypeSafe (typesafe/jev-1.13-20260917)
```

Things worth noticing:

- **Uncertainty is the feature.** On the angry ticket the model split
  billing=0.29 / technical=0.71 — an honest "torn" answer your code can
  threshold on (e.g. escalate when top probability < 0.8).
- **Scores interpolate.** The calm ticket scored 0.69, a weighted mean across
  levels, not just an integer bucket.
- **No prose, no parsing.** The response is valid by construction — nothing to
  regex or schema-validate.
