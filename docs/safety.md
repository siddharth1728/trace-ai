# TRACE Safety Model & Sandbox Boundaries

TRACE is designed for educational debugging investigations on student Python code. Because student code is untrusted and may contain unintentional infinite loops, large print statements, or broken logic, TRACE enforces strict safety boundaries.

---

## 1. Safety Controls in v0.1

### A. Subprocess Isolation
* Submitted code is **never executed in-process** with the TRACE application.
* Each execution creates a temporary workspace directory and spawns an independent Python interpreter subprocess (`sys.executable`).
* The temporary directory is cleaned up immediately upon completion.

### B. Environment Sanitization (Secret Scrubbing)
* The subprocess environment is stripped of all sensitive environment variables:
  * API keys (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, etc.)
  * Cloud credentials (`AWS_*`, `GCP_*`, `AZURE_*`)
  * Database URLs (`DATABASE_URL`)
  * Passwords, auth headers, and tokens
* Only standard runtime variables (`PATH`, `SYSTEMROOT`, `TEMP`, `PYTHONPATH`) are passed.

### C. Execution Timeouts
* Default timeout is **5.0 seconds** (configurable up to a maximum of 15.0 seconds).
* When a timeout occurs, the parent process terminates the entire subprocess tree (using `taskkill /F /T` on Windows or `SIGKILL` on POSIX systems).
* Prevents CPU starvation from infinite `while True:` loops.

### D. Output Truncation Limits
* Standard output and standard error streams are capped at **10 KB (10,240 bytes)**.
* Prevents memory exhaustion attacks from scripts that spam large strings (`print('A' * 1000000)`).

### E. Path Containment (Jail Check)
* File access is restricted to the designated workspace root or temp directory.
* Resolves symlinks and canonical paths to block path traversal attempts (`../../windows/system32`).

---

## 2. Explicit Security Limitations & Non-Goals

> [!WARNING]
> **Educational Development Sandbox vs. Enterprise Virtualization**:
> TRACE v0.1's safety boundaries are designed for local development and student code bugs. They **do not constitute a security-hardened enterprise sandbox** against adversarial kernel exploits, memory corruption, or low-level OS abuse.
>
> * **No Network Namespace Isolation in v0.1:** Subprocesses currently share host network interfaces.
> * **No Linux cgroups / gVisor Containerization:** v0.1 runs directly on the host OS subprocess layer.
>
> For future production multi-tenant deployments (v1.0+), execution will integrate container-level isolation (e.g., Docker, WebAssembly / WASI, or gVisor sandbox runtimes).
