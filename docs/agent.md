# TRACE Agent & Investigation Loop

TRACE's agent loop coordinates goal understanding, dynamic planning, hypothesis tracking, evidence evaluation, counterexample verification, and claim validation.

---

## 1. Investigation Loop Flow (v0.2)

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
       │   [EXTRACT EVIDENCE]
       │   (DIRECT vs DERIVED)
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
Tools Finished / Sufficient Evidence?
       │
      YES
       │
       ▼
   [TESTING]
 (Generate & execute targeted
  counterexample disproof test)
       │
       ▼
  [VERIFYING]
 (Deterministic multi-evidence
  verification & calibration)
       │
       ▼
 [CLAIM VALIDATION]
 (Audit & ground all factual claims)
       │
       ▼
  [DIAGNOSING] ──► [EXPLAINING] ──► [COMPLETED]
```

---

## 2. Hypothesis Lifecycle & Verification States (v0.2)

TRACE maintains competing candidate explanations with a verified evidence lifecycle:

| Status | Meaning | Grounding & Verification Rules |
| :--- | :--- | :--- |
| **`PROPOSED`** | Initial candidate explanation generated during planning. | None (initial belief state). Confidence: $0.20$. |
| **`SUPPORTED`** | Observation evidence aligns with this explanation. | Requires $\ge 1$ successful observation linking to this hypothesis. Confidence: $0.50 - 0.80$. |
| **`WEAKENED`** | Observation evidence reduces likelihood of this explanation. | Evidence points toward an alternate root cause. Confidence: $0.20$. |
| **`REJECTED`** | Direct contradictory evidence disproves this explanation. | Observed facts disprove hypothesis (e.g. AST proved valid syntax). Confidence: $0.10$. |
| **`VERIFICATION_PENDING`** | Leading candidate undergoing targeted counterexample challenge. | Counterexample test being constructed. Confidence: $0.65$. |
| **`VERIFIED`** | Hypothesis passed both direct observation and targeted countercheck. | $\ge 1$ direct supporting evidence + passed countercheck experiment with 0 disproofs (or deterministic AST syntax error). Confidence: $0.90 - 0.95$. |
| **`DISPROVEN`** | Counterexample experiment or direct tool fact disproved hypothesis. | Countercheck failed on predicted-safe inputs or direct contradiction found. Confidence: $\le 0.25$. |

---

## 3. Stopping Criteria & Anti-Premature Termination

The agent loop terminates when any of the following conditions are met:
1. **Conclusive Verification**: Leading hypothesis is `VERIFIED` with confidence $\ge 90\%$ backed by direct tool evidence and passed countercheck.
2. **Deterministic Syntax Verification**: AST static analysis deterministically proves syntax coordinates.
3. **Plan Completion**: All planned steps are finished and verification stage completes.
4. **Iteration Limit**: Configured `max_iterations` (default: 8) is reached to prevent runaway looping.
5. **Safety Block**: Security violation triggers transition to `BLOCKED`.
