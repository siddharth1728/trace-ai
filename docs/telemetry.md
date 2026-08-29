# TRACE Telemetry & Debugging Intelligence Architecture

> **Understand your bugs. Understand how you debug.**

TRACE isolates evidence-based debugging from behavioral telemetry to guarantee **100% auditable facts** without synthetic ML hallucinations or fake student archetypes.

---

## 1. The Four Telemetry Namespaces

To prevent data contamination between what the student does, what the AI agent does, and what the code looks like, TRACE enforces four explicit telemetry namespaces:

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        TRACE TELEMETRY SYSTEM                          │
├──────────────────────────┬─────────────────────────────────────────────┤
│ 1. STUDENT_TELEMETRY     │ Student hypotheses, test inputs, revisions  │
│ 2. TRACE_AGENT_TELEMETRY │ Planned steps, tool calls, counterchecks    │
│ 3. PROBLEM_TELEMETRY     │ User goal, error description, traceback     │
│ 4. CODE_TELEMETRY        │ LOC, AST depth, cyclomatic complexity, AST  │
└──────────────────────────┴─────────────────────────────────────────────┘
```

### Namespace Specifications

| Namespace | Category | Captured Metrics & Signals |
| :--- | :--- | :--- |
| **`STUDENT_TELEMETRY`** | Human Action | Articulated bug hypotheses, confidence ratings, custom test expressions, code revision diffs (`lines_added`, `lines_deleted`, `complexity_delta`), Socratic reflections. |
| **`TRACE_AGENT_TELEMETRY`**| Autonomous Agent | Investigation step count, tool execution sequence, observation outcomes, candidate hypotheses, countercheck generation & execution, evidence links, calibrated confidence. |
| **`PROBLEM_TELEMETRY`** | Task Context | Natural language goal length, error description string, presence/absence of raw Python traceback text, error family categorization (`SyntaxError`, `TypeError`, `ValueError`, etc.). |
| **`CODE_TELEMETRY`** | Code Structure | AST node count, AST maximum tree depth, function count, cyclomatic complexity, imported modules, recursion indicators. |

---

## 2. The 18-Feature Process Vector

Each completed investigation session extracts an 18-dimensional numerical and categorical telemetry vector persisted into the relational `session_telemetry` table:

```python
@dataclass
class TelemetryFeatures:
    session_id: str
    data_source: str  # "REAL" or "BENCHMARK"
    problem_id: str
    
    # Structural Code Metrics
    loc: int
    ast_node_count: int
    ast_max_depth: int
    cyclomatic_complexity: int
    function_count: int
    
    # Error Framing
    has_traceback_input: bool
    error_desc_length: int
    error_family_syntax: bool
    error_family_type_or_value: bool
    
    # Investigation Behavior
    ast_first_step: bool
    static_to_exec_ratio: float
    failed_tool_ratio: float
    tool_sequence_entropy: float
    total_investigation_steps: int
    
    # Scientific Falsification Rigor
    hypothesis_count: int
    hypothesis_rejection_ratio: float
    countercheck_execution_rate: float
    direct_evidence_ratio: float
```

### Key Formulae

1. **Tool Sequence Entropy ($H$)**:
   $$H = - \sum_{i=1}^{K} p_i \log_2(p_i)$$
   Measures whether tool usage was focused and systematic or erratic and exploratory.

2. **Direct Evidence Ratio**:
   $$\text{DER} = \frac{\text{Count of DIRECT empirical evidence items}}{\text{Total extracted evidence items}}$$

3. **Countercheck Execution Rate**:
   $$\text{CER} = \frac{\text{Executed Counterchecks}}{\text{Total Formulated Hypotheses}}$$

---

## 3. Deterministic Habit Profiling (0% Fake ML)

In accordance with strict pedagogical ethics, TRACE rejects training synthetic machine learning models that assign arbitrary personality archetypes. Instead, the **Student Debugging Profile** computes deterministic, mathematically verifiable metrics:

* **Static AST Inspection Rate**: Percentage of sessions where the student or system inspected syntax/structure prior to execution.
* **Traceback Framing Rate**: Percentage of debugging tasks submitted with concrete traceback logs.
* **Countercheck Rigor**: Frequency of attempting targeted edge-case falsification before accepting a diagnosis.
* **Code Modification Churn**: Incremental lines added/deleted and cyclomatic complexity shifts between code revision iterations.

---

## 4. Telemetry Export CLI

TRACE provides built-in CLI commands to export anonymized telemetry for offline research and pedagogical data quality audits:

```bash
# Export all telemetry records to JSON
trace-cli export telemetry --output dataset.json --format json

# Export to CSV for tabular analysis in Pandas / R
trace-cli export telemetry --output dataset.csv --format csv

# Generate a markdown quality report
trace-cli export dataset-report --output quality_report.md
```
