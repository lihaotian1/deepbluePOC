# API610 Web Project Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a React + FastAPI + Docker web app for PDF chunking, knowledge-base matching, and Excel export.

**Architecture:** FastAPI provides document APIs, OpenAI-compatible semantic matching, SSE streaming, and Excel export. React handles upload, markdown editing/preview, real-time comparison rendering, and export trigger.

**Tech Stack:** FastAPI, Pydantic, httpx, openpyxl, React, Vite, TypeScript, react-markdown, fetch-event-source, Docker Compose.

---

### Task 1: Project skeleton and dependencies

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/api/__init__.py`
- Create: `frontend/package.json`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/styles/theme.css`

**Step 1: Write failing checks**

Run:

```bash
python -m pytest backend/tests -q
```

Expected: fails because backend files are missing.

**Step 2: Implement minimal scaffold**

- Create backend package and health endpoint.
- Create frontend app shell.

**Step 3: Verify**

Run:

```bash
python -m pytest backend/tests -q
```

Expected: test discovery succeeds after tests are added.

### Task 2: Session and knowledge-base services

**Files:**
- Create: `backend/app/schemas.py`
- Create: `backend/app/services/session_store.py`
- Create: `backend/app/services/kb_loader.py`

**Step 1:** Add tests for KB parsing and type extraction.

**Step 2:** Implement in-memory store and KB flattening.

**Step 3:** Run targeted tests and confirm pass.

### Task 3: Upload / split / edit APIs

**Files:**
- Create: `backend/app/api/document_routes.py`
- Create: `backend/app/services/splitter_service.py`

**Step 1:** Add tests that assert upload returns ordered chunks and `doc_id`.

**Step 2:** Implement upload + patch chunk APIs.

**Step 3:** Verify tests pass.

### Task 4: OpenAI-compatible matching and SSE compare

**Files:**
- Create: `backend/app/services/llm_client.py`
- Create: `backend/app/services/prompt_builder.py`
- Create: `backend/app/services/matcher_service.py`
- Create: `backend/app/api/compare_routes.py`

**Step 1:** Add tests for matcher fallback paths (other category, no item hit).

**Step 2:** Implement two-stage semantic matching and SSE event stream.

**Step 3:** Verify tests pass.

### Task 5: Excel export

**Files:**
- Create: `backend/app/services/export_service.py`
- Create: `backend/app/api/export_routes.py`
- Create: `backend/tests/test_export_service.py`

**Step 1:** Add failing test asserting workbook columns/sheets.

**Step 2:** Implement export builder and API download endpoint.

**Step 3:** Verify pass.

### Task 6: React UI and streaming UX

**Files:**
- Create: `frontend/src/pages/HomePage.tsx`
- Create: `frontend/src/components/UploadPanel.tsx`
- Create: `frontend/src/components/ChunkCard.tsx`
- Create: `frontend/src/components/ComparePanel.tsx`
- Create: `frontend/src/components/ResultTag.tsx`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/sse.ts`

**Step 1:** Add basic UI smoke test scaffold.

**Step 2:** Implement upload/edit/compare/export user flow.

**Step 3:** Build frontend and verify no compile errors.

### Task 7: Docker and documentation

**Files:**
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `.env.example`
- Create: `README.md`

**Step 1:** Add run instructions and env docs.

**Step 2:** Build containers and verify startup.

### Task 8: Final verification

**Step 1:** Run backend tests.

```bash
python -m pytest backend/tests -q
```

**Step 2:** Build frontend.

```bash
npm --prefix frontend run build
```

**Step 3:** Smoke run with Docker compose.

```bash
docker compose up --build
```
