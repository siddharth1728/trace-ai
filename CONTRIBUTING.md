# Contributing to TRACE v1.0

Thank you for your interest in TRACE! TRACE is an evidence-driven AI debugging investigation product developed as an engineering portfolio project.

---

## 1. Development Guidelines

* **Code Style**:
  * Python: Follow PEP 8 guidelines. Use typing hints across all functions and models.
  * TypeScript/React: Strictly enforce clean type definitions in `src/types/index.ts`. Avoid `any` types where possible.
* **Testing**:
  * All Python changes must include corresponding unit or integration tests in `tests/`.
  * Verify that `python -m pytest -v tests/` passes 100% of tests.
  * Ensure `npx tsc --noEmit` and `npm run build` succeed before opening a pull request.
* **Architecture Principles**:
  * **Zero Hallucination Gate**: Never bypass empirical tool verification or allow ungrounded claims in final diagnoses.
  * **Telemetry Isolation**: Maintain strict boundary separation between student actions, agent actions, problem context, and code properties.

---

## 2. Commit Expectations

Write concise, clear commit messages describing the change:
- `feat: Add student test input execution to interactive mode`
- `fix: Correct evidence ratio string comparison logic`
- `docs: Add 15 technical interview questions and architecture guide`

---

## 3. Project Structure Overview

```text
c:\TRACE
├── docs/             # Technical architecture specs & interview guides
├── frontend/         # React 18 + Vite + TypeScript web studio
├── src/trace/        # Core Python agent, API routes, database models, CLI
└── tests/            # Unit, integration, and E2E benchmark suites
```
