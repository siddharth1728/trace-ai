# TRACE v1.0 Canonical Demo Cases

This document outlines the three canonical demo cases for testing and presenting TRACE v1.0 Student MVP.

---

## Demo Case 1: Straightforward Bug (Verified Diagnosis)

### Objective
Demonstrate automated Guided Mode investigation, AST inspection, sandbox execution, counterexample disproof, and 100% grounded diagnosis.

### Source Code
```python
def get_user_profile(user_db, user_id):
    user = user_db.get(user_id)
    return {
        "id": user_id,
        "name": user.get("name").upper(),
        "role": user.get("role", "member")
    }

database = {1: {"name": "Alice", "role": "admin"}, 2: {}}
print(get_user_profile(database, 2))
```

### Steps to Run
1. Open TRACE in browser (`http://localhost:5173`) or CLI.
2. Select **Guided Mode**.
3. Set Goal: `Debug crash when formatting user name with None`.
4. Error Message: `AttributeError: 'NoneType' object has no attribute 'upper'`.
5. Click **Start Investigation**.

### Expected Outcome
* **Verification Status**: `VERIFIED ROOT CAUSE` (Confidence: 100%).
* **Root Cause**: `user.get("name")` returns `None` for user `2`, causing `.upper()` to fail on `NoneType`.
* **Countercheck**: Executed safely in sandbox and verified fix logic.
* **Learning Takeaway**: Explains dictionary `.get()` defaults and defensive `None` checks in Python.

---

## Demo Case 2: Misleading / Wrong Student Hypothesis (Disproven & Re-investigated)

### Objective
Demonstrate Interactive Mode where a student's initial hypothesis is incorrect. TRACE runs a sandbox experiment, marks the hypothesis `DISPROVEN`, explains *why* it was disproven, and leads the student to the true root cause.

### Source Code
```python
def create_customer_record(name, orders=[]):
    orders.append("signup_bonus")
    return {"name": name, "order_history": orders}

customer1 = create_customer_record("Alice")
customer2 = create_customer_record("Bob")

print(f"Customer 1: {customer1}")
print(f"Customer 2: {customer2}")
```

### Steps to Run
1. Select **Interactive Mode**.
2. Set Goal: `Fix bug where order history is bleeding between customers`.
3. Submit Student Hypothesis: *"The string append function is throwing a runtime exception."*
4. Run Test Input: `create_customer_record("Test")`.

### Expected Outcome
* **Student Hypothesis Status**: `DISPROVEN` (Test executed cleanly without string exception).
* **TRACE Explanation**: Explains that `.append()` succeeded, but observed state retention across calls.
* **Alternative Cause Identified**: `VERIFIED ROOT CAUSE` — Mutable default argument `orders=[]` retains state across function calls in Python.

---

## Demo Case 3: Insufficient Evidence (Visible Uncertainty & Low Confidence)

### Objective
Demonstrate TRACE's zero-hallucination guarantee when evidence is insufficient or external dependencies are missing. TRACE refuses to fabricate certainty.

### Source Code
```python
import json

def load_app_config():
    with open('/etc/app_config.json', 'r') as f:
        return json.load(f)

def initialize_system():
    config = load_app_config()
    print(f"Starting system with mode: {config.get('mode', 'default')}")

initialize_system()
```

### Steps to Run
1. Select **Guided Mode**.
2. Set Goal: `Debug script failing to process config file`.
3. Observed Error: `FileNotFoundError: [Errno 2] No such file or directory: '/etc/app_config.json'`.
4. Click **Start Investigation**.

### Expected Outcome
* **Verification Status**: `UNVERIFIED / BLOCKED` (Low confidence: 20%).
* **Zero Hallucination**: TRACE does NOT invent a fake config file or generate unverified code replacements.
* **Remaining Uncertainties**: Explicitly lists missing external file `/etc/app_config.json` and environmental prerequisites.
