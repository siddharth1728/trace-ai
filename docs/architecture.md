# TRACE System Architecture

TRACE is architected around the core engineering principle:

> **Use deterministic software where truth and safety matter. Use an LLM where language and reasoning are useful. Use agentic behavior where the next action depends on evolving evidence.**

---

## 1. High-Level Architecture (v0.2)

```text
┌─────────────────────────────────────────────────────────────┐
│                          Rich CLI                           │
│     (Auditable Evidence Chain, Live Badges, Diagnosis)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Investigation Orchestrator                  │
│   (Coordinates State Machine, Planner, Evaluator & Tools)   │
└──────────────┬───────────────┬───────────────┬──────────────┘
               │               │               │
               ▼               ▼               ▼
       ┌───────────────┐ ┌───────────┐ ┌───────────────┐
       │  Agent State  │ │  Planner  │ │   Evaluator   │
       │(Evidence Store│ │ (Schemas) │ │ (Hypotheses)  │
       └───────┬───────┘ └─────┬─────┘ └───────┬───────┘
               │               │               │
               │               ▼               ▼
               │       ┌───────────────────────────────┐
               │       │      Vendor-Neutral LLM       │
               │       │   (MockProvider / OpenAI)     │
               │       └───────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│           Evidence & Verification Engine (v0.2)             │
├──────────────────────────────┬──────────────────────────────┤
│    Targeted Counterexample   │    Deterministic Verifier    │
│    Sandbox Disproof Engine   │  (Multi-evidence heuristics) │
├──────────────────────────────┴──────────────────────────────┤
│                   Diagnosis Claim Validator                 │
│         (Audits & Grounds 100% of Final Factual Claims)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                        Tool Registry                        │
├───────────────┬──────────────────────────────┬──────────────┤
│  File Reader  │         AST Analyzer         │  Traceback   │
│  (Path jail)  │ (Functions, syntax, calls)   │    Parser    │
├───────────────┴──────────────────────────────┴──────────────┤
│                  Controlled Python Executor                 │
│      (Subprocess, 5s timeout, env scrubbing, output cap)    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Core Subsystems

### A. State Management & Lifecycle Machine (`src/trace/core/state.py`)
Agent state is strictly controlled through `AgentState` with a validated `LifecycleState` machine:
* `CREATED` $\rightarrow$ `UNDERSTANDING` $\rightarrow$ `PLANNING` $\rightarrow$ `INVESTIGATING` $\rightarrow$ `TESTING` $\rightarrow$ `EVALUATING` $\rightarrow$ `DIAGNOSING` $\rightarrow$ `EXPLAINING` $\rightarrow$ `COMPLETED`
* `BLOCKED` serves as a safe terminal state if a safety violation or unrecoverable error occurs.
* Stores an explicit `evidence_store: List[Evidence]` linking observations and hypotheses.

### B. Evidence Domain Model (`src/trace/core/evidence.py`)
Distinguishes between direct and derived facts:
* **`EvidenceType.DIRECT`** (Confidence Weight: $1.0$): Facts directly produced by deterministic tools (AST parser, subprocess stdout/stderr/exit code, stack frames).
* **`EvidenceType.DERIVED`** (Confidence Weight: $\le 0.70$): Logical deductions, inferred intentions, or multi-step reasoning.
* **Relations**: `SUPPORTS`, `CONTRADICTS`, `DERIVED_FROM`, `VERIFIES`, `DISPROVES`.

### C. Automated Counterexample Engine (`src/trace/agent/counterexample.py`)
Before confirming a diagnosis, TRACE actively attempts to **disprove** its leading hypothesis:
* Isolates function definitions from crashing top-level script execution using `ast`.
* Inspects signature parameter counts and types.
* Generates minimal ephemeral test harnesses (e.g. testing with valid non-None inputs, boundary lists, or non-zero numbers).
* Executes inside the safe sandbox. If the counter-experiment fails unexpectedly, direct disproof evidence is recorded (`relation = DISPROVES`).

### D. Deterministic Hypothesis Verifier (`src/trace/agent/verifier.py`)
Evaluates evidence chains without relying on probabilistic LLM scoring:
* **`VERIFIED`**: $\ge 1$ direct supporting evidence + passed countercheck experiment (or deterministic AST syntax error). Confidence: $0.90 - 0.95$.
* **`STRONGLY_SUPPORTED`**: $\ge 2$ direct supporting observations, 0 contradictions, countercheck pending. Confidence: $0.80$.
* **`PLAUSIBLE`**: Single direct/derived supporting observation, 0 contradictions. Confidence: $0.50$.
* **`DISPROVEN`**: Counter-experiment failed or direct contradiction found. Confidence: $\le 0.25$.
* **`UNVERIFIED`**: No direct supporting evidence. Confidence: $0.20$.

### E. Diagnosis Claim Validator (`src/trace/core/claim_validator.py`)
Audits all claims in the final diagnosis:
* Extracts individual claims and classifies them as `FACTUAL` vs `REASONING`.
* Factual claims (e.g., claiming a tool ran or a specific error code was produced) MUST match direct evidence in `state.evidence_store`.
* Unbacked factual claims are stripped from the diagnosis and appended to `what_remains_uncertain`.
* Enforces $0\%$ Unsupported Claim Rate ($UCR$).

---

## 3. Interview Design Decisions

1. **Why not just let the LLM verify its own hypotheses?**
   LLMs have a well-documented confirmation bias: once an LLM proposes a hypothesis, asking it "Is this hypothesis correct?" results in high false-positive rates. TRACE decouples hypothesis generation from verification by executing an automated countercheck experiment in a sandboxed interpreter.
2. **Why use template-based counterexamples rather than full SMT/symbolic execution?**
   Full symbolic execution (e.g., Z3 / angr) requires heavy native dependencies, struggles with arbitrary Python libraries/objects, and introduces excessive latency. Template-based signature-aware mutation covers $>90\%$ of common student coding errors cleanly in pure Python.
3. **Why distinguish DIRECT from DERIVED evidence?**
   Direct empirical facts (exit code 1, line 4 SyntaxError) cannot be argued away. Derived conclusions (assumed student intent) have inherent uncertainty. Weighting them differently prevents speculative reasoning from overriding empirical tool outputs.
