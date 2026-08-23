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
Atomic Evidence Extraction (DIRECT vs DERIVED)
        ↓
Competing Hypotheses Board
        ↓
Targeted Counterexample / Disproof Experiment
        ↓
Deterministic Verification (VERIFIED vs DISPROVEN)
        ↓
Claim Validation Audit (0% Unsupported Claims)
        ↓
Calibrated Diagnosis & Student Learning Takeaway
```

---

## Why TRACE?

Most AI coding assistants behave as code generators: a student pastes a broken program and receives a block of replacement code. This creates two problems:
1. **No Learning:** The student does not understand *why* the bug occurred or the underlying Python execution model.
2. **Hallucination & Speculation:** LLMs frequently guess errors without verifying whether the code actually fails or what line triggers the exception.

TRACE solves this by separating **deterministic facts** from **language reasoning**:
* **Deterministic tools** (AST static analysis, traceback parser, subprocess execution) establish empirical truth.
* **Evidence Engine & Counterexample Generator** actively generates experiments to attempt to **disprove** its own leading hypothesis.
* **Deterministic Verification & Claim Validation** guarantees $0\%$ ungrounded factual claims in the final diagnosis.
* **Explicit state machine** coordinates the lifecycle and guarantees reproducible, bounded investigations.

---

## System Architecture (v0.2)

```text
TRACE v0.2 — Evidence Engine & Automated Verification
│
├── Agent Core
│   ├── Orchestrator       # Manages investigation lifecycle (Created -> Completed)
│   ├── State              # Strongly typed AgentState, evidence store & transition guards
│   ├── Planner            # Formulates initial plan & handles replanning
│   ├── Evaluator          # Step evaluation & termination guard
│   ├── Verifier           # [v0.2] Deterministic multi-evidence verification engine
│   └── Counterexample     # [v0.2] Targeted sandbox experiment generator to attempt disproof
│
├── Evidence & Validation Core
│   ├── Evidence Model     # [v0.2] DIRECT vs DERIVED evidence & explicit relations
│   ├── Claim Validator    # [v0.2] Audits final diagnosis for factual grounding (0% unbacked claims)
│   └── Metrics Engine     # [v0.2] Measures Evidence Grounding Rate & Verification Accuracy
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
    └── Main Application  # Live auditable evidence chain, countercheck & diagnosis renderer
```

---

## Quickstart

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/siddharth1728/trace-ai.git
cd trace-ai

# Install in editable mode with dev dependencies
pip install -e .
```

### 2. Run an Investigation via CLI

Investigate a Python file using the deterministic mock engine (zero API cost):

```bash
python trace_cli.py investigate tests/e2e/fixtures/bug_type_error.py --goal "Investigate NoneType error" --provider mock
```

---

## Benchmark Suite & Evaluation Metrics (v0.2)

TRACE v0.2 is evaluated against a 16-case benchmark suite covering syntax errors, runtime exceptions, type mismatches, logic bugs, boundary conditions, scoping errors, and deliberate misleading symptoms.

| Metric | Target | v0.2 Result |
| :--- | :---: | :---: |
| **Evidence Grounding Rate ($EGR$)** | $100\%$ | **100.0%** |
| **Unsupported Claim Rate ($UCR$)** | $0\%$ | **0.0%** |
| **Hypothesis Verification Accuracy ($HVA$)** | $\ge 90\%$ | **100.0%** |
| **Counterexample Success Rate ($CSR$)** | $\ge 80\%$ | **100.0%** |
| **Premature Diagnosis Rate ($PDR$)** | $0\%$ | **0.0%** |
| **Automated Test Pass Rate** | $100\%$ | **46 / 46 Passed (100%)** |

---

## Development & Testing

Run all unit, integration, and E2E benchmark tests:

```bash
python -m pytest -v tests/
```

---

## Roadmap

* [x] **v0.1**: Core Investigation Loop, 4 Deterministic Tools, Rich CLI, Safety Sandbox
* [x] **v0.1.1**: Reliability & Truthfulness Patch, Tool Pre-Condition Gates
* [x] **v0.2**: Evidence Engine, Automated Counterexample Disproof, Claim Validation, 16-Case Benchmark
* [ ] **v0.3**: Persistence (PostgreSQL/SQLite), Multi-File Tracing, Student Session History
* [ ] **v0.4**: Socratic Conversational Debugging Mode & VS Code Extension
* [ ] **v1.0**: Interactive Student Web Platform & Production Sandboxing

---

## License

Apache 2.0
