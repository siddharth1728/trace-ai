# TRACE Agent & Investigation Loop

TRACE's agent loop coordinates goal understanding, dynamic planning, hypothesis tracking, and evidence evaluation.

---

## 1. Investigation Loop Flow

```text
               USER GOAL
                   │
                   ▼
            [UNDERSTANDING]
                   │
                   ▼
              [PLANNING]
         (Generate 2-3 hypotheses
          & sequential plan steps)
                   │
                   ▼
       ┌──► [INVESTIGATING]
       │           │
       │           ▼
       │     [SELECT TOOL]
       │           │
       │           ▼
       │     [EXECUTE TOOL]
       │           │
       │           ▼
       │    [RECORD OBSERVATION]
       │           │
       │           ▼
       │      [EVALUATING]
       │ (Update hypothesis status
       │  & confidence with evidence)
       │           │
       ├── Refuted? ──► [REPLANNING] ──┐
       │                               │
       │◄──────────────────────────────┘
       │
Enough Evidence / Max Iterations?
       │
      YES
       │
       ▼
  [DIAGNOSING] ──► [EXPLAINING] ──► [COMPLETED]
```

---

## 2. Competing Hypothesis System

TRACE maintains competing candidate explanations for every bug:

| Status | Meaning |
| :--- | :--- |
| **`PROPOSED`** | Initial candidate explanation generated during planning. |
| **`SUPPORTED`** | Observation evidence aligns with this explanation (confidence increases). |
| **`WEAKENED`** | Observation evidence reduces likelihood of this explanation. |
| **`REJECTED`** | Direct contradictory evidence disproves this explanation (e.g. AST proved code is syntactically valid). |
| **`CONFIRMED`** | Deterministic evidence conclusively proves this root cause (confidence $\ge 0.90$). |

---

## 3. Stopping Criteria

The agent loop terminates when any of the following conditions are met:
1. **Conclusive Evidence**: A hypothesis is `CONFIRMED` with confidence $\ge 90\%$.
2. **Explicit Decision**: Evaluator requests `FINALIZE_DIAGNOSIS`.
3. **Plan Completion**: All planned steps are finished and no further tools are requested.
4. **Iteration Limit**: Configured `max_iterations` (default: 8) is reached to prevent infinite loops.
5. **Safety Block**: Security violation triggers transition to `BLOCKED`.
