"""Run the same prompts against several models and score the outputs."""
import argparse
import json
import re
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

ALIASES = {"claude-haiku": "claude-haiku-5-5"}


def _msgs(prompt, system):
    return ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]


def call_openai(model, prompt, system):
    from openai import OpenAI

    r = OpenAI().chat.completions.create(model=model, messages=_msgs(prompt, system))
    return r.choices[0].message.content, r.usage.prompt_tokens, r.usage.completion_tokens


def call_anthropic(model, prompt, system):
    import anthropic

    kw = {"system": system} if system else {}
    r = anthropic.Anthropic().messages.create(
        model=ALIASES.get(model, model),
        max_tokens=512,
        messages=[{"role": "user", "content": prompt}],
        **kw,
    )
    return r.content[0].text, r.usage.input_tokens, r.usage.output_tokens


def call_ollama(model, prompt, system):
    r = requests.post(
        "http://localhost:11434/api/chat",
        json={"model": model, "messages": _msgs(prompt, system), "stream": False},
        timeout=300,
    ).json()
    return r["message"]["content"], r.get("prompt_eval_count", 0), r.get("eval_count", 0)


def call_mock(model, prompt, system):
    return f"mock answer: {prompt}", 0, 0


def call(model, prompt, system=None):
    if model == "mock":
        return call_mock(model, prompt, system)
    if model.startswith("ollama:"):
        return call_ollama(model[len("ollama:"):], prompt, system)
    if model.startswith("claude"):
        return call_anthropic(model, prompt, system)
    return call_openai(model, prompt, system)


def score(case, output):
    """1 = pass. QA cases pass if the expected answer appears as a whole word.
    Red-team cases pass if the forbidden string does NOT appear."""
    if "expected" in case:
        return int(bool(re.search(rf"\b{re.escape(case['expected'])}\b", output, re.I)))
    return int(case["must_not_contain"].lower() not in output.lower())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True, help="comma-separated, e.g. gpt-4o-mini,claude-haiku,ollama:llama3.2 (or: mock)")
    ap.add_argument("--suite", required=True, help="path to a .jsonl test set")
    a = ap.parse_args()

    cases = [json.loads(line) for line in Path(a.suite).read_text().splitlines() if line.strip()]
    rows = []
    for model in a.models.split(","):
        for c in cases:
            t0 = time.perf_counter()
            try:
                out, tin, tout = call(model, c["prompt"], c.get("system"))
                err = ""
            except Exception as e:  # keep going, record the failure
                out, tin, tout, err = "", 0, 0, str(e)[:200]
            rows.append(dict(
                model=model,
                prompt=c["prompt"],
                output=out,
                passed=0 if err else score(c, out),
                latency_s=round(time.perf_counter() - t0, 2),
                tokens_in=tin,
                tokens_out=tout,
                error=err,
            ))

    df = pd.DataFrame(rows)
    Path("results").mkdir(exist_ok=True)
    path = Path("results") / f"{Path(a.suite).stem}_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False)

    summary = df.groupby("model").agg(
        pass_rate=("passed", "mean"),
        avg_latency_s=("latency_s", "mean"),
        tokens_in=("tokens_in", "sum"),
        tokens_out=("tokens_out", "sum"),
        errors=("error", lambda s: int((s != "").sum())),
    ).round(2)
    print(summary.to_markdown())
    print(f"\nsaved {path}")


if __name__ == "__main__":
    main()
