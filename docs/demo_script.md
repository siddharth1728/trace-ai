# TRACE v1.0 — 3–5 Minute Live Demonstration Script

This script provides a 3-5 minute live demonstration sequence highlighting TRACE's evidence-driven investigation, counterexample disproof, interactive collaborative debugging, and deterministic habit analytics.

---

## Live Demo Sequence

### ⏱️ 0:00 — Introduction (30 seconds)
> *"Most AI coding assistants act as code generators: you paste broken code, and they return replacement snippets without verifying if the code actually fails or explaining why it broke. TRACE is different. It is an evidence-driven debugging agent for Python students that conducts scientific investigations grounded in AST analysis, sandbox runs, counterexample disproof, and 0% unsupported claims."*

---

### ⏱/0:30 — Submit Bug & Launch Guided Mode (30 seconds)
1. Open **`http://localhost:5173`**.
2. Point out the clear home studio tagline: *"Understand your bugs. Understand how you debug."*
3. Select the **Verified Root Cause** sample program (`get_user_profile` with missing `name` key).
4. Select **Guided Mode** and click **Start Investigation**.
5. Show real-time Server-Sent Events (SSE) streaming as TRACE creates an investigation plan, runs static AST analysis, and executes the program in the safety sandbox.

---

### ⏱️ 1:00 — Show Evidence & Competing Hypotheses (60 seconds)
1. Switch to the **Possible Causes** tab in the center pipeline.
2. Point out TRACE's candidate hypotheses (e.g., *Missing dict key returns None causing AttributeError* vs *Invalid user_id type*).
3. Switch to the **Why TRACE Believes This** tab.
4. Highlight atomic `DIRECT` evidence extracted directly from successful tool runs, showing full provenance linking back to empirical observations.

---

### ⏱️ 2:00 — Show Countercheck Disproof & Verified Diagnosis (30 seconds)
1. Click **TRACE Tested Its Conclusion** tab.
2. Explain: *"Before confirming a diagnosis, TRACE constructs an isolated countercheck harness to actively attempt to disprove its leading theory."*
3. Point to the **Diagnosis & Learning** pane on the right:
   - **`VERIFIED ROOT CAUSE`** badge with calibrated 100% confidence.
   - **Student Learning Takeaway** explaining Python's `.get()` default handling.
   - **Conceptual Fix Guidance** providing educational guidance rather than dumping unverified code.

---

### ⏱️ 2:30 — Switch to Interactive Collaborative Mode (60 seconds)
1. Click **New Investigation** and select **Interactive Mode**.
2. Enter Goal: *"Fix bug where order history bleeds between customers"*.
3. Submit a **Student Hypothesis**: *"The append function throws an exception."*
4. Run a **Custom Sandbox Test**: `create_customer_record("Test")`.
5. Show TRACE marking the student hypothesis **`DISPROVEN`** because the test executed cleanly, then re-investigating and isolating the true root cause: **Mutable Default Argument (`orders=[]`)**.
6. Open the **Your Actions** tab to showcase the **Interaction Timeline** logging the chronological dialogue turns between student and agent.

---

### ⏱️ 3:30 — Show Profile & Privacy Settings (30 seconds)
1. Navigate to the **Profile** tab:
   - Highlight **Observed Debugging Habits** (100% deterministic facts: AST inspection rate, traceback framing rate, countercheck disproof rigor).
   - Point out that TRACE uses **zero fake ML psychological archetypes**.
2. Navigate to **Settings**:
   - Show the **Analytics Opt-In/Opt-Out** toggle and explain strict 4-namespace telemetry isolation.

---

### ⏱️ 4:00 — Wrap Up & Recruiter Architecture Takeaway (30 seconds)
> *"To summarize: TRACE is a complete full-stack agent project featuring a React 18 frontend, FastAPI backend, SQLite persistence, SSE streaming, multi-tool orchestrator, counterexample disproof engine, and 75/75 passing automated tests."*
