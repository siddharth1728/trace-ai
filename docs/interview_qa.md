# TRACE v1.0 — Technical Interview Questions & Architecture QA

This document contains 15 technical questions and honest implementation answers about the TRACE system architecture.

---

### Q1: Why is TRACE built as an agent rather than a single LLM prompt?
**Answer**: A single LLM prompt suffers from two critical flaws: no empirical verification and high hallucination risk. LLMs guess code replacements without running the code or checking stack traces. TRACE is an agent because it coordinates a state machine (`CREATED` -> `RUNNING` -> `COMPLETED` / `BLOCKED`), executes deterministic tools (AST analysis, subprocess sandbox), collects empirical evidence (`DIRECT` vs `DERIVED`), formulates competing hypotheses, and runs counterexample disproof before making a diagnosis.

### Q2: How does TRACE separate deterministic facts from LLM reasoning?
**Answer**: Deterministic tools (`FileReaderTool`, `ASTAnalyzerTool`, `TracebackParserTool`, `PythonExecutorTool`) produce `Observation` records. The `EvidenceEngine` wraps successful observations into `Evidence` items with assigned confidence weights ($1.0$ for direct execution, $\le 0.70$ for derived reasoning). The LLM is restricted to proposing plans and hypotheses, while the `Verifier` and `ClaimValidator` evaluate evidence programmatically without LLM speculation.

### Q3: How does TRACE prevent unsupported factual claims in final diagnoses?
**Answer**: The `ClaimValidator` (`src/trace/core/claim_validator.py`) inspects the generated diagnosis against the session's `Observation` store. It classifies claims as `FACTUAL` vs `REASONING`. Any factual claim referencing a tool or file that was not actually executed cleanly is flagged, penalizing confidence down to $20\%$ and forcing the claim to be stripped or listed under `Remaining Uncertainties`.

### Q4: How does TRACE detect and disprove a wrong student hypothesis?
**Answer**: When a student proposes a hypothesis in Interactive Mode (`StudentHypothesisRecord`), TRACE generates a targeted sandbox test input or countercheck harness (`CountercheckEngine`). If the test runs cleanly without triggering the expected failure, or if stdout contradicts the theory, the `Verifier` marks the student's hypothesis as `DISPROVEN`. TRACE logs the disproof event to the interaction timeline and transitions to re-investigating alternative root causes.

### Q5: How does the Counterexample / Disproof engine work?
**Answer**: The `CounterexampleEngine` (`src/trace/agent/counterexample.py`) inspects candidate hypotheses and active code functions. It constructs isolated Python test harnesses that invoke target functions with edge-case or boundary inputs (e.g., `None`, empty lists `[]`, zero `0`). The harness is executed in the isolated subprocess sandbox. If the execution outcome contradicts the hypothesis falsification condition, the hypothesis status is updated to `DISPROVEN`.

### Q6: How is evidence confidence calculated?
**Answer**: Confidence is **not** an LLM probability score. It is a deterministic mathematical score computed by `DeterministicVerifier` (`src/trace/agent/verifier.py`):
$$\text{Confidence} = w_{\text{base}} + \sum w_{\text{supporting}} - \sum w_{\text{contradictory}} + w_{\text{countercheck}}$$
Where direct observations contribute $+0.30$, verified counterchecks contribute $+0.25$, and failed execution or missing tracebacks incur deterministic penalties.

### Q7: How is code execution isolated in the safety sandbox?
**Answer**: `PythonExecutorTool` (`src/trace/tools/python_executor.py`) runs user Python code in a sandboxed `subprocess.Popen` with strict limits:
- **Timeout Guard**: Kills runaway loops after 5.0 seconds.
- **Output Truncation**: Caps stdout/stderr at 10 KB to prevent memory flooding.
- **Path Containment**: Jails execution to the designated workspace directory.
- **Environment Sanitization**: Strips `API_KEY`, `SECRET`, `PASSWORD`, and system credentials from process environment variables.

### Q8: Why SQLite for local persistence?
**Answer**: SQLite via SQLAlchemy 2.0 Async ORM provides zero-configuration, single-file relational persistence perfect for a student desktop product. It natively supports foreign key cascades (`ON DELETE CASCADE`), index-backed feature queries, transactional consistency across complex relational models (`SessionRecord`, `ObservationRecord`, `EvidenceRecord`, `StudentHypothesisRecord`), and offline operation.

### Q9: Why Server-Sent Events (SSE) instead of WebSockets?
**Answer**: SSE (`/api/sessions/{id}/stream`) provides lightweight, unidirectional HTTP streaming from server to browser. Debugging state updates flow strictly from backend orchestrator to the React frontend UI. SSE handles automatic browser reconnects, simple HTTP/2 multiplexing, and clean lifecycle termination (`event: complete` / `event: error`) without the protocol overhead of full-duplex WebSockets.

### Q10: How is session state persisted across server restarts?
**Answer**: The orchestrator writes full snapshots to SQLite via `SessionRepository.save_full_agent_state()`. All child entities (`plan_steps`, `observations`, `evidence`, `hypotheses`, `counterchecks`, `student_hypotheses`, `code_revisions`) use SQLAlchemy `selectinload` relationships. When the server restarts, `api.getSession(id)` re-hydrates the complete relational model into memory.

### Q11: How do Guided and Interactive modes share the core architecture?
**Answer**: Both modes run on the same `AgentState`, `InvestigationOrchestrator`, and deterministic tool suite. Guided Mode automates tool execution steps sequentially. Interactive Mode introduces state guards (`AWAITING_STUDENT_INPUT`) that pause execution after Socratic questions, allowing students to submit `StudentHypothesisRecord`, `StudentTestInputRecord`, or `CodeRevisionRecord` turns before resuming the orchestrator loop.

### Q12: How are telemetry namespaces separated?
**Answer**: TRACE partitions telemetry into four distinct schemas:
1. `STUDENT_TELEMETRY`: Human actions, student hypotheses, test inputs, revisions.
2. `TRACE_AGENT_TELEMETRY`: Agent steps, tool executions, counterchecks.
3. `PROBLEM_TELEMETRY`: User goal, error message, traceback presence.
4. `CODE_TELEMETRY`: AST metrics, cyclomatic complexity, LOC.
This prevents human actions from corrupting agent metrics or code structural features.

### Q13: Why was Machine Learning classification postponed?
**Answer**: Training a machine learning model (e.g. Random Forest or neural classifier) without real student interaction data yields fake, synthetic predictions. In accordance with rigorous data science principles, TRACE postponed ML training until sufficient real user telemetry is collected via `trace-cli export`. Currently, profile analytics rely 100% on factual, observable habit statistics.

### Q14: How would you introduce ML into TRACE later?
**Answer**: With anonymized datasets exported via `trace export telemetry`, a regularized XGBoost or Random Forest model can be trained to predict student struggle patterns (e.g. *Impulsive Trial-and-Error* vs *Defensive Analyzer*) using the 18-feature process vector. The model would be served via an isolated microservice, serving probability distributions alongside feature attribution (SHAP values).

### Q15: What are TRACE's current limitations?
**Answer**:
1. **Language Scope**: Currently limited to Python source code.
2. **Subprocess Isolation**: Subprocess sandboxing relies on OS process limits rather than full Docker/gVisor containerization.
3. **Multi-file Project Indexing**: Optimized for single-file or lightweight package debugging rather than massive multi-gigabyte codebases.
