# TRACE v1.0 — Environment & Installation Setup Guide

This guide describes how to set up, configure, run, and test TRACE v1.0 from a fresh clone.

---

## 1. Prerequisites

* **Python**: 3.10 or higher
* **Node.js**: 18.0 or higher
* **npm**: 9.0 or higher
* **Git**

---

## 2. Repository Setup

```bash
# Clone the repository
git clone https://github.com/siddharth1728/trace-ai.git
cd trace-ai

# Copy placeholder environment file (optional for offline mock mode)
cp .env.example .env
```

---

## 3. Backend Setup

```bash
# Create and activate a Python virtual environment (recommended)
python -m venv venv

# Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# Linux / macOS:
source venv/bin/activate

# Install TRACE package in editable mode with development dependencies
python -m pip install -e .
```

---

## 4. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install Node dependencies
npm install

# Return to root directory
cd ..
```

---

## 5. Running TRACE Locally

### Option A: Complete Web Application

1. **Start Backend API Server (Port 8000)**:
   ```bash
   python -m trace.api.main
   ```

2. **Start Frontend Dev Server (Port 5173)**:
   ```bash
   cd frontend
   npm run dev
   ```

3. Open **http://localhost:5173** in your web browser.

---

### Option B: Terminal CLI (Zero Setup / Offline Mock)

Run an automated investigation directly in your terminal without starting the backend server or web UI:

```bash
python -m trace.cli.main investigate tests/e2e/fixtures/bug_type_error.py --goal "Investigate NoneType error when formatting username" --provider mock
```

---

## 6. Running Tests & Building Production Bundles

```bash
# Run 75 backend unit, integration, and E2E benchmark tests
python -m pytest -v tests/

# Check frontend TypeScript compilation
cd frontend
npx tsc --noEmit

# Build production bundle
npm run build
```

---

## 7. LLM Provider Configuration

TRACE isolates LLM integration behind a vendor-neutral provider protocol (`src/trace/llm/provider.py`):

* **Mock Provider (Default)**: `TRACE_LLM_PROVIDER=mock`
  - 100% offline, zero API cost, deterministic responses. Perfect for testing and offline demos.
* **OpenAI Provider**: `TRACE_LLM_PROVIDER=openai`
  - Requires setting `OPENAI_API_KEY=your_key_here` in `.env` or system environment.
