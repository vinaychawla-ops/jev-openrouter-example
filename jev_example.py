#!/usr/bin/env python3
"""Basic Jev example via OpenRouter's Decisions API.

Jev is NOT a chat model: you send a `state` plus typed questions, and it
returns calibrated probabilities -- no prose. Three question types:
  - noul   : yes/no  -> probability the answer is "yes" (0..1)
  - choice : pick one of your options -> chosen key + per-option probabilities
  - score  : position on your ordered rubric -> index + per-level probabilities

Endpoint: POST https://openrouter.ai/api/alpha/decisions
(This is separate from /api/v1/chat/completions; chat SDKs will not work.)

Auth: uses the stored `custom.openrouter` credential via authd surrogate --
no raw key in this file or the environment.
"""

import json
import os
import sys
import time
import urllib.request

try:
    sys.path.insert(0, "/opt/hatch/skills/skill-creator/bin")
    from dynamic_credentials import add_surrogate_to_request, read_json_response
    _HAVE_VAULT = True
except ImportError:
    _HAVE_VAULT = False  # running outside Muse: use OPENROUTER_API_KEY env var

    def read_json_response(resp):
        return json.loads(resp.read().decode("utf-8"))

API_URL = "https://openrouter.ai/api/alpha/decisions"
ALLOWED_HOSTS = ("openrouter.ai",)
MODEL = "typesafe/jev-1.13"


def decide(state, questions, model=MODEL):
    """Send one System One request; return (response_dict, latency_ms)."""
    payload = {"model": model, "state": state, "questions": questions}
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if _HAVE_VAULT and not os.environ.get("OPENROUTER_API_KEY"):
        add_surrogate_to_request(req, "custom.openrouter", allowed_hosts=ALLOWED_HOSTS)
    else:
        # Plain local run: export OPENROUTER_API_KEY=<your key>
        key = os.environ.get("OPENROUTER_API_KEY", "")
        if not key:
            raise SystemExit("set OPENROUTER_API_KEY or run inside Muse")
        req.add_header("Authorization", f"Bearer {key}")
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = read_json_response(resp)
    except Exception as exc:
        raise SystemExit(f"request failed: {exc}")
    ms = (time.perf_counter() - t0) * 1000
    if "error" in data:
        raise SystemExit(f"api error: {json.dumps(data['error'])}")
    return data, ms


def show(title, resp, ms):
    print(f"\n=== {title} ({ms:.0f} ms round-trip) ===")
    for name, ans in resp["answers"].items():
        kind = ans["type"]
        if kind == "noul":
            print(f"  [{name}] noul  -> P(yes) = {ans['noul']:.3f}")
        elif kind == "choice":
            probs = ", ".join(f"{k}={v:.3f}" for k, v in ans.get("probabilities", {}).items())
            print(f"  [{name}] choice -> {ans['choice']} (confidence {ans.get('confidence', 0):.3f})")
            print(f"           probs: {probs}")
        elif kind == "score":
            legend = ans.get("legend", {})
            label = legend.get(str(ans["score"]), ans["score"])
            probs = ", ".join(f"{k}={v:.3f}" for k, v in ans.get("probabilities", {}).items())
            print(f"  [{name}] score  -> {ans['score']} ({label}), confidence {ans.get('confidence', 0):.3f}")
            print(f"           probs: {probs}")
    u = resp.get("usage", {})
    print(f"  usage: {u.get('input_tokens')} in / {u.get('output_tokens')} out | "
          f"cost ${u.get('cost', 0):.6f} | served by {resp.get('provider')} ({resp.get('model')})")


QUESTIONS = {
    "urgent": {
        "type": "noul",
        "instructions": "Does this support ticket express urgency?",
    },
    "team": {
        "type": "choice",
        "instructions": "Which team should own this ticket?",
        "criteria": {
            "billing": "Payment, charge, or refund issues",
            "technical": "Bugs or integration failures",
            "sales": "Pricing questions or new purchases",
        },
    },
    "frustration": {
        "type": "score",
        "instructions": "How frustrated is the customer?",
        "criteria": ["Calm", "Concerned but civil", "Very angry"],
    },
}

TICKET_ANGRY = (
    "The payment integration has failed for three days straight. "
    "Every retry charges us twice and support has gone silent. "
    "Fix this TODAY or we are moving to a competitor."
)
TICKET_CALM = (
    "Hi, quick question about our invoice from last month -- "
    "the line item for add-on seats looks higher than we expected. "
    "No rush, just want to understand it when you get a chance."
)


def main():
    for title, ticket in [("Angry ticket", TICKET_ANGRY), ("Calm ticket", TICKET_CALM)]:
        print(f"\nState: {ticket}")
        resp, ms = decide(ticket, QUESTIONS)
        show(title, resp, ms)
    print("\nDone. Notice: no text was generated -- only typed decisions with probabilities.")


if __name__ == "__main__":
    main()
