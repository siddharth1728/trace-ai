# TRACE

> **Understand your bugs. Understand how you debug.**

TRACE is an evidence-driven AI debugging investigation system for Python students.

Instead of jumping straight to replacing code or generating unverified fixes, TRACE treats debugging as a structured scientific investigation:

```text
User Debugging Goal
        ↓
Investigation Plan
        ↓
Deterministic Tools (AST / Traceback / Sandbox Execution)
        ↓
Observations & Facts
        ↓
Competing Hypotheses Board
        ↓
Evidence Evaluation & Replanning
        ↓
Grounded Diagnosis & Student Learning Takeaway
```

---

## Why TRACE?

Most AI coding assistants behave as code generators: a student pastes a broken program and receives a block of replacement code. This creates two problems:
1. **No Learning:** The student does not understand *why* the bug occurred or the underlying Python execution model.
2. **Hallucination & Speculation:** LLMs frequently guess errors without verifying whether the code actually fails or what line triggers the exception.

TRACE solves this by separating **deterministic facts** from **language reasoning**:
* **Deterministic tools** (AST static analysis, traceback parser, subprocess execution) establish hard truth.
* **LLMs** formulate hypotheses, interpret observations, and explain concepts in student-friendly terms.
* **Explicit state machine** coordinates the lifecycle and guarantees reproducible, bounded investigations.

---

## System Architecture (v0.1)

```text
TRACE Core v0.1
│
├── Agent Core
│   ├── Orchestrator       # Manages investigation lifecycle (Created -> Completed)
│   ├── State              # Strongly typed AgentState & transition guards
│   ├── Planner            # Formulates initial plan & handles replanning
│   └── Evaluator          # Updates hypothesis confidence & checks termination
│
├── Tool System
│   ├── Tool Registry      # Central discovery, permission & audit tracking
│   ├── File Reader        # Path-jailed Python source inspection
│   ├── AST Analyzer       # Deterministic static syntax & structure extractor
│   ├── Python Executor    # Controlled subprocess with timeout & output caps
│   └── Traceback Parser   # Normalizes exception frames and root cause line
│
├── LLM Layer
│   ├── Provider Protocol  # Vendor-neutral LLM abstraction
│   ├── Mock Provider      # Fast, zero-cost, 100% deterministic offline engine
│   ├── OpenAI / LLM       # Real provider adapter (OpenAI, LiteLLM, Ollama, etc.)
│   ├── Schemas            # Validated Pydantic models for all agent outputs
│   └── Prompts            # Pedagogical, evidence-first system instructions
│
├── Safety Sandbox
│   ├── Timeout Guard      # Kills runaway infinite loops (default 5.0s)
│   ├── Output Truncation  # Caps memory & terminal flooding (10KB limit)
│   ├── Path Containment   # Blocks directory traversal attacks
│   └── Env Sanitization   # Strips API keys, credentials, and tokens from subprocess
│
└── Rich CLI
    └── Main Application  # Live investigation dashboard & diagnosis renderer
```

---

## Quickstart

### 1. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/your-username/TRACE.git
cd TRACE
python -m pip install -e ".[dev]"
```

### 2. Run an Investigation via CLI

Investigate a Python file using the built-in offline mock provider:

```bash
python trace_cli.py investigate tests/e2e/fixtures/bug_runtime_error.py --goal "Investigate ZeroDivisionError on empty score list"
```

Or using an OpenAI-compatible API key:

```bash
set OPENAI_API_KEY=your_key_here
python trace_cli.py investigate your_script.py --goal "Why does this return None?" --provider openai
```

---

## Running the Test Suite

TRACE includes a full test suite with unit tests, safety boundary verification, and 5 benchmark student bug classes (syntax error, runtime error, type error, logic error, input validation bug):

```bash
# Run all tests
python -m pytest -v tests/
```

Test breakdown:
* `tests/unit/test_state.py`: Lifecycle state machine and state transition guards.
* `tests/unit/test_tools.py`: Deterministic AST analyzer, traceback parser, and file reader.
* `tests/unit/test_executor_safety.py`: Infinite loop timeouts, output truncation caps, environment secret scrubbing, and path jail containment.
* `tests/integration/test_agent_loop.py`: Full orchestrator loop with mock provider.
* `tests/e2e/test_e2e_investigations.py`: 5 standard student bug benchmarks.

---

## Milestone Roadmap

* **v0.1 — Investigation Core (Current Milestone):** Deterministic tool suite, state machine, controlled execution sandbox, vendor-neutral LLM provider abstraction, and Rich CLI.
* **v0.2 — Evidence Engine & Automated Verification:** Graph of hypotheses, formal evidence linking, and automated counter-example generation.
* **v0.3 — Product Layer & Persistence:** Session persistence (PostgreSQL / SQLite), REST API endpoints, and interactive student timeline interface.
* **v0.4 — Learning & Telemetry:** Student debugging mistake classification and telemetry pattern analysis.
* **v1.0 — Evaluated Portfolio Product:** Benchmark evaluation over 50+ real-world student debugging sessions.

---

## Safety & Limitations Notice

> [!WARNING]
> TRACE v0.1 enforces subprocess execution with timeouts, process tree termination, output caps, environment variable stripping, and path containment. This provides a safe development boundary for typical student scripting bugs, but is **not claimed to be a hardened enterprise virtualization/container sandbox** (e.g. gVisor/Firecracker). Do not expose v0.1 as an untrusted public multi-tenant remote execution service.
# trace-ai
