# TRACE — The Engineering & Architecture Story

This document tells the story of building TRACE v1.0, highlighting key architectural decisions, early failures, reliability corrections, and engineering judgment.

---

## 1. The Core Problem
Most AI coding tools act as code generators. A student pastes a broken Python script, and the AI returns a replaced block of code. This creates two problems:
1. **No Student Learning**: The student does not understand *why* the code broke or how Python executed it.
2. **Hallucination & Speculation**: LLMs guess root causes without executing the code or verifying stack traces.

I set out to build **TRACE**: an evidence-driven AI agent that investigates bugs scientifically, gathers empirical proof, disproves wrong theories, and explains the root cause to the student.

---

## 2. Failed Initial Assumption & The Evidence Problem
My initial attempt relied on standard agentic LLM prompting. I assumed that if I gave the LLM access to tools (AST analyzer, Python executor), it would naturally use them accurately.

However, detailed testing revealed a critical flaw: **evidence leakage and hallucinated certainty**. The LLM would occasionally claim *"The traceback proves line 5 failed"* even when no traceback was provided, or claim a hypothesis was confirmed when the underlying tool call had failed.

---

## 3. The Reliability Correction: Claim Validation & Verification
To solve this, I decoupled **language reasoning** from **empirical verification**:
* **Direct vs Derived Evidence**: Created an explicit `Evidence` domain model distinguishing direct tool facts ($1.0$ weight) from derived inferences ($\le 0.70$ weight).
* **Claim Validator**: Built an auditing engine (`src/trace/core/claim_validator.py`) that programmatically parses final diagnoses. If a diagnosis claims a tool ran or a file had a specific error that is missing from the `Observation` store, the diagnosis is penalized and the claim is stripped.
* **Pre-Condition Gates**: Added guards to prevent executing tools when required inputs (like raw stack traces) are absent.

---

## 4. The Counterexample Engine (Falsification Rigor)
Confirmation bias is a major issue in AI debugging: once an LLM finds one plausible explanation, it stops looking.

To enforce scientific rigor, I built the **Counterexample Engine** (`src/trace/agent/counterexample.py`). Before confirming a leading hypothesis, TRACE generates an isolated test harness in a sandboxed subprocess to actively attempt to **disprove** its own theory. If the counter-test succeeds without failing, the hypothesis is marked `DISPROVEN`, and TRACE re-investigates alternative causes.

---

## 5. Productization: Full-Stack Web Studio
To make TRACE accessible to students:
* **Backend**: FastAPI REST API and async SQLite persistence via SQLAlchemy 2.0.
* **Real-Time Streaming**: Server-Sent Events (SSE) broadcasting live agent state updates to the browser without WebSocket overhead.
* **Frontend**: React 18 + Vite + TypeScript + Tailwind CSS built around a responsive 3-pane layout: Code Editor, Investigation Pipeline, and Diagnosis & Learning Pane.

---

## 6. Socratic Interactive Debugging Mode
Recognizing that debugging is collaborative, I added **Interactive Mode**:
* Students can articulate their own hypotheses, run custom Python expressions in the sandbox, and submit incremental code revisions.
* TRACE tracks structural AST diffs (`lines_added`, `lines_deleted`, `cyclomatic_complexity_delta`) and poses reflective Socratic questions.
* Includes a seamless *"Let TRACE Take Over"* button to return to Guided mode at any point.

---

## 7. Telemetry & Why Machine Learning Was Deliberately Postponed
Early iterations attempted to use a synthetic Random Forest model to classify student "behavioral archetypes."

During my engineering audit, I recognized a fundamental flaw: **training an ML model on synthetic/fake student data produces meaningless predictions.** 

I made the deliberate decision to **tear down the synthetic ML model** and replace it with a **100% Deterministic Habit Profiler** based on factual, observable statistics (static AST inspection rate, traceback framing rate, countercheck disproof rigor). I created `trace export telemetry` CLI tools to export real 18-feature process vectors for future research when sufficient real user data is collected.

---

## 8. Summary
TRACE evolved from a simple LLM wrapper into a robust, auditable agent product with 75/75 passing automated tests, 0% unsupported claims, and production-ready full-stack architecture.
