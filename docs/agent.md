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

## 2. Competing Hypothesis System & Support Rules

TRACE maintains competing candidate explanations for every bug:

| Status | Meaning | Grounding Requirement |
| :--- | :--- | :--- |
| **`PROPOSED`** | Initial candidate explanation generated during planning. | None (initial belief state). |
| **`SUPPORTED`** | Observation evidence aligns with this explanation. | **Mandatory:** `supporting_obs_id` must point to an existing observation with `is_success == True`. |
| **`WEAKENED`** | Observation evidence reduces likelihood of this explanation. | Evidence points toward an alternate root cause. |
| **`REJECTED`** | Direct contradictory evidence disproves this explanation. | Observed facts disprove hypothesis (e.g. AST proved valid syntax). |
| **`CONFIRMED`** | Deterministic evidence conclusively proves this root cause. | **Mandatory:** Deterministic observation (AST syntax error or reproducible sandbox error). |

---

## 3. Stopping Criteria & Anti-Premature Termination

The agent loop terminates when any of the following conditions are met:
1. **Conclusive Evidence**: A hypothesis is `CONFIRMED` with confidence $\ge 85\%$ backed by verified successful observations.
2. **Explicit Decision**: Evaluator requests `FINALIZE_DIAGNOSIS` (rejected if 0 successful observations exist and pending steps remain).
3. **Plan Completion**: All planned steps are finished and no further tools are requested.
4. **Iteration Limit**: Configured `max_iterations` (default: 8) is reached to prevent infinite loops.
5. **Safety Block**: Security violation triggers transition to `BLOCKED`.
