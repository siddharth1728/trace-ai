# TRACE Project Roadmap

TRACE is developed incrementally through defined engineering milestones.

---

## 🎯 Milestone v0.1 — Investigation Core ✅

**Goal**: Prove that an AI agent can execute an evidence-driven debugging investigation using deterministic tools, explicit state, and competing hypotheses without hallucinating code replacements.

**Delivered Features**:
* Explicit `AgentState` with validated `LifecycleState` machine.
* Deterministic Tool Suite: `FileReaderTool`, `ASTAnalyzerTool`, `TracebackParserTool`, `PythonExecutorTool`.
* Controlled Execution Sandbox: Subprocess isolation, 5s timeout, 10KB output cap, secret scrubbing, and path jail.
* Vendor-Neutral LLM Provider layer with `MockLLMProvider` (100% offline, zero-cost tests) and `OpenAICompatibleProvider`.
* Competing Hypothesis tracking board with evidence linking and confidence updating.
* Rich CLI interface with live event stream rendering and student-focused final diagnosis.

---

## 🎯 Milestone v0.1.1 — Evidence-Grounding & Reliability Patch ✅

**Goal**: Eliminate diagnosis hallucination, premature termination, and failed-tool evidence leakage.

**Delivered Features**:
* Tool Pre-Condition Gates (skips `traceback_parser` when traceback input is missing).
* Hypothesis Support Verification Gate (requires verified successful observation ID).
* Evaluator anti-premature termination guard (blocks termination when 0 successful observations exist).
* Programmatic diagnosis grounding (claims only tools that actually ran).
* Regression test suite guaranteeing 100% evidence-grounded diagnoses.

---

## 🎯 Milestone v0.2 — Evidence Engine & Automated Verification ✅

**Goal**: Move from "the agent has evidence" to *"every important conclusion has an auditable evidence chain, and TRACE actively attempts to disprove its own diagnosis."*

**Delivered Features**:
* **Evidence Domain Model (`src/trace/core/evidence.py`)**: Distinguishes `DIRECT` ($1.0$ weight) vs `DERIVED` ($\le 0.70$ weight) facts and explicit relations (`SUPPORTS`, `CONTRADICTS`, `DERIVED_FROM`, `VERIFIES`, `DISPROVES`).
* **Automated Counterexample Engine (`src/trace/agent/counterexample.py`)**: Targeted sandbox test harness generator that tests candidate functions against safe inputs to actively challenge hypotheses.
* **Deterministic Hypothesis Verifier (`src/trace/agent/verifier.py`)**: Multi-evidence rule engine establishing `VERIFIED` ($\ge 90\%$), `STRONGLY_SUPPORTED`, `PLAUSIBLE`, `DISPROVEN` ($\le 25\%$), and `UNVERIFIED` ($20\%$).
* **Diagnosis Claim Validator (`src/trace/core/claim_validator.py`)**: Audits final diagnoses, classifying claims into `FACTUAL` vs `REASONING` and strictly enforcing $0\%$ ungrounded factual claims.
* **Rich CLI Auditable Evidence Table & Status Badges**: Displays complete evidence provenance and countercheck outcomes.
* **16-Case Benchmark Suite & Metrics Calculator (`src/trace/eval/metrics.py`)**: Achieves $100\%$ Evidence Grounding Rate, $0\%$ Unsupported Claim Rate, $100\%$ Hypothesis Verification Accuracy, and 100% test pass rate.

---

## 🎯 Milestone v0.3 — Product Layer & Persistence ✅

**Goal**: Enable long-running student session history, interactive timeline visualization, and multi-file tracking.

**Delivered Features**:
* Local SQLite database persistence (SQLAlchemy 2.0 async ORM).
* REST API endpoints (`/api/sessions`, `/api/sessions/{id}/investigate`, `/api/sessions/{id}/events`).
* Real-time Server-Sent Events (SSE) streaming state changes directly to the browser.
* 3-Pane React + Vite + TypeScript web interface: Code Editor, Investigation Pipeline, and Diagnosis Pane.

---

## 🎯 Milestone v0.4 — Learning & Telemetry Intelligence ✅

**Goal**: Capture partitioned debugging process metrics and compute deterministic habit profiles.

**Delivered Features**:
* 4-Namespace Telemetry isolation (`STUDENT_TELEMETRY`, `TRACE_AGENT_TELEMETRY`, `PROBLEM_TELEMETRY`, `CODE_TELEMETRY`).
* 18-Feature process extraction vector.
* 100% Deterministic Habit Profiler (Static AST inspection rate, traceback framing rate, countercheck rigor, tool failure rate).
* Telemetry Export CLI (`trace export telemetry`, `trace export dataset-report`) for JSON/CSV datasets.

---

## 🎯 Milestone v0.5 — Collaborative Interactive Debugging Mode ✅

**Goal**: Enable collaborative, Socratic debugging where students articulate hypotheses and run custom sandbox experiments.

**Delivered Features**:
* Dual Mode Architecture: **Guided Mode** (automated) vs **Interactive Mode** (collaborative dialogue).
* Student Hypothesis Formulation & Agent Counter-Verification.
* Student Sandbox Test Execution with isolated stdout/stderr capture.
* Incremental Code Revisions with structural AST diffing (`lines_added`, `lines_deleted`, `cyclomatic_complexity_delta`).
* Socratic Reflection Inquiries with seamless "Let TRACE Take Over" mode handoff.
* Interaction Timeline component rendering chronological dialogue turns.
* Privacy & Analytics Settings page with opt-in/opt-out toggles.

---

## 🎯 Milestone v1.0 — Student MVP Complete ✅

**Delivered Features**:
* Complete end-to-end Python debugging platform with 75/75 passing automated tests.
* Zero fake ML hallucinations, full evidence grounding, and production-ready React web app.
