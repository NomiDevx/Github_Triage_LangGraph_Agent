# GitHub Issue Triage Agent

An agentic system that triages GitHub issues using **DeepSeek** via LangChain and **LangGraph**.

> **This system only suggests.** It never writes to GitHub, never edits files, never deletes anything.

---

## Quickstart

```bash
# 1. Copy and fill in your API key
cp .env.example .env
# edit .env and set DEEPSEEK_API_KEY=...

# 2. Run on a sample issue
python main.py sample_issues/bug_example.txt

# 3. Run the Next.js Web UI
cd web
npm run dev
# open http://localhost:3000 in your browser

# 4. Run tests
python -m pytest tests/ -v
```

---

## Next.js Web UI

A modern web dashboard built with Next.js and Tailwind CSS is available in `web/`:
- **Interactive Triage Workspace**: Type an issue or pick a quick preset, configure code search folder, and view classifications, completeness analysis, and suggested replies.
- **Evaluation Dashboard**: Run the 10-issue evaluation dataset live and inspect the real-time confusion matrix and per-sample logs.

```bash
cd web
npm install
npm run dev
```

---

## Project layout

```
src/triage/
  config.py        # All settings and magic numbers — change them here
  models.py        # Pydantic schemas + TriageState TypedDict
  llm.py           # Builds the DeepSeek LLM client (once)
  prompts.py       # All prompts as named constants
  nodes/
    classify.py    # Node 1: bug / feature_request / question / docs
    missing_info.py  # Node 2: completeness check + draft reply  (Stage 2)
    code_search.py   # Agent: find related files in a local folder (Stage 4)
  tools.py         # Sandboxed file-system tools for the code-search agent
  graph.py         # Assembles and compiles the LangGraph
main.py            # CLI entry point
evals/
  dataset.jsonl    # Labeled sample issues
  run_evals.py     # Accuracy + confusion matrix
tests/             # pytest unit and integration tests
```

---

## Stages

| Stage | What it adds |
|-------|-------------|
| **1** ✅ | Classify node, graph skeleton, CLI, unit tests |
| **2** | Missing-info node — completeness check + draft reply |
| **3** | Sandboxed code-search tools with security tests |
| **4** | Code-search agent + conditional edge (bugs only) |
| **5** | Eval dataset + accuracy script |

---

## Configuration

All tunable values live in `src/triage/config.py`:

| Setting | Default | Purpose |
|---------|---------|---------|
| `model_name` | `deepseek-chat` | DeepSeek model ID |
| `model_temperature` | `0.0` | LLM temperature (0 = deterministic) |
| `max_code_search_steps` | `10` | Hard cap on agent tool calls |
| `max_file_read_chars` | `8000` | Truncation limit for read_file |
| `max_search_results` | `10` | Max paths returned by search_code |

---

## Issue file format

```
First line is the issue title
Everything after that is the body.

Markdown is fine.
```

---

## Security

The code-search tools are sandboxed to a single configured folder.
They resolve all paths with `pathlib.Path.resolve()` and reject anything
that escapes the root (including `../` traversal and symlinks).
`.env`, `.git`, `node_modules`, `.venv`, and binary files are always skipped.
