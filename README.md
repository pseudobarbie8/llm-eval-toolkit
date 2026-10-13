# llm-eval-toolkit

Compare LLMs on cost, latency, quality, and prompt-injection robustness using custom test sets.

```bash
pip install -r requirements.txt
python run.py --models gpt-4o-mini,claude-haiku,ollama:llama3.2 --suite suites/qa.jsonl
python run.py --models ollama:llama3.2 --suite suites/redteam.jsonl
```

Output goes to `results/` as a CSV plus a markdown table.

## Test set format

```json
{"prompt": "What is the capital of Morocco?", "expected": "Rabat"}
```

## What it does

- Sends the same prompts to each model
- Scores with exact match or an LLM judge
- Logs latency and token cost per call
- Red-team suite checks whether a model leaks its system prompt or follows injected instructions

## Notes

API keys go in `.env` (see `.env.example`). Ollama must be running for local models.

Tests: `pytest`

MIT
