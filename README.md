# TRACE

> **Understand your bugs. Understand how you debug.**

---

## What is TRACE?

TRACE is an evidence-driven AI debugging investigation product for Python students. Instead of generating unverified code replacements, TRACE conducts an empirical, hypothesis-driven scientific investigation grounded in static AST analysis, sandboxed execution, atomic evidence extraction, counterexample disproof testing, and 100% grounded diagnoses.

---

## The Problem

Most AI coding assistants act as code generators. When a student pastes a broken Python script, the AI returns a block of replacement code without verifying if the code actually fails or explaining why it broke. This creates two major issues:
1. **No Student Learning**: The student copies the fix without understanding Python's execution model or how to debug.
2. **AI Speculation & Hallucination**: LLMs frequently guess root causes without executing the code or verifying stack traces.

---

## What Makes TRACE Different?

```text
Traditional AI Assistant:
  Problem ─────────────────────────────────────────────► Replacement Code (Unverified)

TRACE Evidence Engine:
  Problem ──► Plan ──► Investigate ──► Hypotheses ──► Evidence ──► Countercheck ──► Verification ──► Grounded Diagnosis
```

---

## Key Capabilities

* 🔬 **Deterministic Evidence Engine**: Gathers empirical facts via AST static analysis, traceback parsing, and isolated subprocess runs.
* ⚔️ **Counterexample Disproof Engine**: Generates targeted sandbox test harnesses to actively challenge and attempt to *disprove* leading hypotheses before making a diagnosis.
* 🤝 **Interactive Collaborative Mode**: Enables students to articulate bug theories, execute custom sandbox test cases, and track code revision iterations.
* 💬 **Socratic Debugging Inquiries**: Guides student understanding with targeted reflection questions and a seamless *"Let TRACE Take Over"* mode handoff.
* 📊 **100% Deterministic Habit Analytics**: Computes factual habit stats (static inspection rate, traceback framing, countercheck rigor) with zero synthetic ML hallucinations.
* 🔒 **4-Namespace Telemetry Isolation**: Segregates student actions, agent actions, problem context, and code properties with full privacy opt-out controls and CLI export tools (`trace export telemetry`).

---

## System Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                           User / Web Browser                            │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│             React 18 + TypeScript + Vite + Tailwind CSS UI              │
│     [Code Pane]     [Investigation Pipeline]     [Diagnosis Studio]     │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ (REST API & Real-Time SSE Stream)
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend & Session Service                    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     Investigation Orchestrator                          │
│   ├── State Machine      ├── Evidence Engine (DIRECT vs DERIVED)        │
│   ├── Planner            ├── Verifier & Claim Validator (0% unbacked)   │
│   └── Hypotheses Board   └── Counterexample Disproof Engine             │
└──────────────────┬───────────────────────────────────┬──────────────────┘
                   │                                   │
                   ▼                                   ▼
┌──────────────────────────────────────┐  ┌───────────────────────────────┐
│      Deterministic Tool Suite        │  │   Async SQLite Persistence    │
│  • AST Analyzer   • Subprocess Sandbox│  │      (SQLAlchemy 2.0 ORM)     │
│  • Traceback Parse• Path-Jailed Reader│  │  Sessions, Evidence, Telemetry│
└──────────────────────────────────────┘  └───────────────────────────────┘
```

---

## Example Investigation

Given a Python script with an error:
```python
def get_user_profile(user_db, user_id):
    user = user_db.get(user_id)
    return {"id": user_id, "name": user.get("name").upper()}

database = {1: {"name": "Alice"}, 2: {}}
print(get_user_profile(database, 2))
```

1. **AST & Sandbox Run**: TRACE executes the script in the sandbox, capturing `AttributeError: 'NoneType' object has no attribute 'upper'`.
2. **Evidence Extraction**: Extracts direct evidence showing `user.get("name")` evaluates to `None` for user `2`.
3. **Counterexample Disproof**: Runs a test harness passing dictionary entries with missing keys to confirm the disproof boundary.
4. **Grounded Diagnosis**: Reports `VERIFIED ROOT CAUSE` (100% confidence) with conceptual fix guidance explaining dictionary `.get()` defaults.

---

## Guided vs. Interactive Modes

* **Guided Mode (Automated)**: TRACE autonomously plans steps, runs tools, tests hypotheses, and produces a verified diagnosis. Ideal for rapid root-cause analysis.
* **Interactive Mode (Collaborative)**: Pauses for student input. Students formulate bug hypotheses, run custom sandbox test cases, and submit code revisions while TRACE tracks structural AST diffs (`+lines`, `-lines`, `CC Δ`). Includes a *"Let TRACE Take Over"* button to return to Guided mode anytime.

---

## Safety Boundary Notice

> **Note**: Subprocess sandboxing in TRACE is designed as a **development and student safety boundary** (enforcing a 5.0s timeout, 10 KB output truncation cap, workspace directory path containment, and environment variable secret scrubbing). It is not an enterprise-grade multi-tenant isolated container runtime (such as Docker or gVisor).

---

## Evaluation & Test Metrics

TRACE is evaluated against a 16-case benchmark suite and 75 automated tests:

| Evaluation Metric | Target | Verified Result |
| :--- | :---: | :---: |
| **Evidence Grounding Rate ($EGR$)** | $100\%$ | **100.0%** |
| **Unsupported Claim Rate ($UCR$)** | $0\%$ | **0.0%** |
| **Hypothesis Verification Accuracy ($HVA$)** | $\ge 90\%$ | **100.0%** |
| **Counterexample Success Rate ($CSR$)** | $\ge 80\%$ | **100.0%** |
| **Automated Test Pass Rate** | $100\%$ | **75 / 75 Passed (100%)** |
| **Frontend TypeScript Check** | 0 Errors | **0 Errors** |

---

## Tech Stack

* **Core Agent & Backend**: Python 3.10+, FastAPI, AsyncIO, Typer CLI
* **Persistence & Database**: SQLite, SQLAlchemy 2.0 Async ORM, aiosqlite
* **Real-Time Streaming**: Server-Sent Events (SSE) via sse-starlette
* **Frontend UI Studio**: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons
* **LLM Abstraction**: Vendor-neutral provider protocol with 100% offline `MockLLMProvider` and `OpenAICompatibleProvider`

---

## Project Structure

```text
trace-ai/
├── docs/                     # Technical specifications & interview guides
│   ├── audit_report.md       # Final product audit & evaluation results
│   ├── demo_cases.md         # 3 canonical reproducible demo cases
│   ├── demo_script.md        # 3-5 minute live demonstration script
│   ├── interview_qa.md       # 15 technical interview questions & architecture Q&A
│   ├── project_metrics.md    # Recorded performance measurements & test counts
│   ├── resume_bullets.md     # Resume bullet points & verbal summaries
│   ├── setup.md              # Environment setup & installation guide
│   ├── story.md              # The engineering story behind TRACE
│   └── telemetry.md          # 4 telemetry namespaces & 18-feature vector spec
├── frontend/                 # React 18 + Vite + TypeScript studio
│   ├── src/components/       # CodePane, Pipeline, Diagnosis, Timeline
│   ├── src/pages/            # InvestigatePage, HistoryPage, ProfilePage, SettingsPage
│   └── src/api/              # Typed fetch API & SSE hooks
├── src/trace/                # Core Python package
│   ├── agent/                # Orchestrator, Planner, Verifier, Counterexample
│   ├── api/                  # FastAPI routes (sessions, profile, sse)
│   ├── cli/                  # Typer CLI (investigate, export)
│   ├── core/                 # State machine, Evidence Engine, Claim Validator
│   ├── db/                   # SQLAlchemy models, repository, sessions
│   └── tools/                # AST analyzer, Python executor, Traceback parser
├── tests/                    # Unit, integration, and E2E benchmark suites
└── .env.example              # Placeholder environment variables
```

---

## Running Locally

```bash
# 1. Install backend package in editable mode
pip install -e .

# 2. Run backend API server
python -m trace.api.main

# 3. Start frontend dev server
cd frontend
npm install
npm run dev

# 4. Run automated test suite
python -m pytest -v tests/
```

---

## Current Limitations

1. **Python Scope**: Focused exclusively on Python 3.10+ code debugging.
2. **Single-Process Subprocess Isolation**: Uses OS subprocess limits rather than containerized micro-sandboxes.
3. **Lightweight Project Scope**: Optimized for single-file and small-package debugging rather than multi-gigabyte repositories.

---

## Future Work & Why Machine Learning Was Postponed

During development, an initial machine learning model (Random Forest) was trained on synthetic data to predict student behavior patterns. An engineering audit revealed that **training ML models on synthetic student data produces meaningless predictions**.

In accordance with rigorous data science ethics, the synthetic ML model was **deliberately torn down** and replaced with a **100% Deterministic Habit Profiler** based on factual, observable stats.

Future ML classification work is planned as a research phase **only after sufficient real student interaction datasets are collected** using the built-in `trace export telemetry` CLI tools.

---

## License

Apache 2.0
