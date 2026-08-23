# TRACE System Architecture

TRACE is architected around the core engineering principle:

> **Use deterministic software where truth and safety matter. Use an LLM where language and reasoning are useful. Use agentic behavior where the next action depends on evolving evidence.**

---

## 1. High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                          Rich CLI                           │
│     (Event listener, live hypothesis board, diagnosis)      │
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
       │ (Typed model) │ │ (Schemas) │ │ (Hypotheses)  │
       └───────────────┘ └─────┬─────┘ └───────┬───────┘
                               │               │
                               ▼               ▼
                       ┌───────────────────────────────┐
                       │      Vendor-Neutral LLM       │
                       │   (MockProvider / OpenAI)     │
                       └───────────────────────────────┘
                               ▲
                               │
┌──────────────────────────────┴──────────────────────────────┐
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
* The LLM cannot mutate state directly. Only orchestrator logic processes tool results and updates state.

### B. Tool System (`src/trace/tools/`)
Tools are deterministic components registered in `ToolRegistry`:
* **`FileReaderTool`**: Reads Python source with line slicing, rejecting files $>256\text{ KB}$ and path traversals.
* **`ASTAnalyzerTool`**: Uses Python's standard `ast` library to identify syntax errors (with exact line/offset coordinates), functions, classes, imports, assignments, and recursive structures without executing code.
* **`TracebackParserTool`**: Normalizes exception strings into structured frames, root cause line, and exception type.
* **`PythonExecutorTool`**: Subprocess executor inside temporary directories with timeout enforcement, output caps, and environment variable sanitization.

### C. LLM Abstraction Layer (`src/trace/llm/`)
* **Vendor-Neutral Interface**: `LLMProvider` protocol enables switching between mock testing and real API backends (OpenAI, Anthropic, Gemini, local models via LiteLLM/Ollama).
* **Mock Provider**: High-fidelity, zero-cost, deterministic rule-based provider for offline testing and continuous integration.
* **Structured Schemas**: All agent decisions, plans, and diagnoses use Pydantic validation (`InitialPlanSchema`, `NextActionDecision`, `DiagnosisSchema`).

---

## 3. Interview Design Decisions

1. **Why not hardcode the tool sequence?**
   Different bugs require different investigative paths. A syntax error only needs static AST parsing, whereas a nondeterministic logic failure requires controlled execution and reproduction.
2. **Why use subprocess execution instead of `exec()` or `eval()`?**
   `eval()` and `exec()` execute in-process, sharing memory, globals, and credentials with the TRACE runtime. Running in a separate subprocess with an isolated environment prevents student code from corrupting agent memory or accessing sensitive secrets.
3. **Why structured schemas over freeform text prompts?**
   Structured Pydantic validation eliminates parsing fragility and guarantees that the orchestrator receives well-typed actions, hypothesis scores, and evidence links.
