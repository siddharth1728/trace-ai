# TRACE Project Roadmap

TRACE is developed incrementally through defined milestones.

---

## 🎯 Current Milestone: v0.1 — Investigation Core ✅

**Goal**: Prove that an AI agent can execute an evidence-driven debugging investigation using deterministic tools, explicit state, and competing hypotheses without hallucinating code replacements.

**Delivered Features**:
* Explicit `AgentState` with validated `LifecycleState` machine.
* Deterministic Tool Suite: `FileReaderTool`, `ASTAnalyzerTool`, `TracebackParserTool`, `PythonExecutorTool`.
* Controlled Execution Sandbox: Subprocess isolation, 5s timeout, 10KB output cap, secret scrubbing, and path jail.
* Vendor-Neutral LLM Provider layer with `MockLLMProvider` (100% offline, zero-cost tests) and `OpenAICompatibleProvider`.
* Competing Hypothesis tracking board with evidence linking and confidence updating.
* Rich CLI interface with live event stream rendering and student-focused final diagnosis.
* 100% passing test suite across Unit, Integration, and 5 student bug benchmarks.

---

## 🔜 Milestone v0.2 — Evidence Engine & Automated Verification

**Goal**: Deepen hypothesis verification with formal evidence graphs and counter-example generation.
* Formal Evidence Engine (bipartite graph connecting Observation nodes to Hypothesis nodes).
* Automated counter-example generation (synthesizing targeted minimal test inputs to refute edge-case hypotheses).
* Expanded benchmark suite of 25 labeled student bugs.

---

## 🔜 Milestone v0.3 — Product Layer & Persistence

**Goal**: Enable long-running student session history and interactive timeline visualization.
* Local SQLite / PostgreSQL database persistence.
* REST API endpoints (`/sessions`, `/sessions/{id}/investigate`, `/sessions/{id}/events`).
* Interactive web timeline interface showing step-by-step investigation unfolding.

---

## 🔜 Milestone v0.4 — Learning & Student Debugging Telemetry

**Goal**: Analyze student debugging behaviors over time.
* Telemetry collection on common student stumbling blocks (e.g. repeated off-by-one errors, unhandled None returns).
* Machine Learning classification model (Random Forest baseline) on structured telemetry.
* Personalized learning recommendations.

---

## 🔜 Milestone v1.0 — Evaluated Portfolio Product

**Goal**: Comprehensive evaluation across 50+ real-world student debugging sessions.
* Quantitative benchmarks measuring diagnosis accuracy, evidence validity, cost, latency, and hallucination reduction vs baseline LLM prompting.
* Public demonstration repository with reproducible evaluation scripts.
