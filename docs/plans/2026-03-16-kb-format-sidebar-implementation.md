# Dual Format Knowledge Base And Homepage Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add dual-format knowledge-base compatibility, file create/delete, search/pagination, and finish the requested sidebar/homepage copy and card layout refinements.

**Architecture:** FastAPI extends knowledge-base management with format-aware load/save plus file lifecycle APIs. React keeps one editor surface, but toggles behavior by knowledge-base format while the app shell/sidebar and homepage cards get targeted UI refinements.

**Tech Stack:** FastAPI, Pydantic, React, TypeScript, Vite, existing axios client, existing pytest suite.

---

### Task 1: Backend tests for dual-format KB and file lifecycle

**Files:**
- Modify: `backend/tests/test_knowledge_base_service.py`
- Modify: `backend/tests/test_knowledge_base_api.py`

**Step 1: Write the failing test**

Add tests for:
- detecting `grouped` vs `flat_key_value`
- converting flat key-value docs into tree-like response model
- saving flat key-value docs back to original format
- creating a new knowledge-base file
- deleting a knowledge-base file

**Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_knowledge_base_service.py backend/tests/test_knowledge_base_api.py -q`
Expected: FAIL because format fields and file lifecycle APIs do not exist.

**Step 3: Write minimal implementation**

Implement format-aware manager and create/delete routes.

**Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_knowledge_base_service.py backend/tests/test_knowledge_base_api.py -q`
Expected: PASS.

### Task 2: Backend schemas and knowledge-base manager

**Files:**
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/knowledge_base_manager.py`
- Modify: `backend/app/api/knowledge_base_routes.py`

**Step 1:** Use Task 1 tests as red.

**Step 2:** Add `format` metadata, file create/delete request models, and format-aware read/save conversion.

**Step 3:** Re-run Task 1 tests and verify pass.

### Task 3: Homepage and sidebar UI refinement

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/components/UploadPanel.tsx`
- Modify: `frontend/src/components/ComparePanel.tsx`
- Modify: `frontend/src/styles/theme.css`

**Step 1: Write the failing check**

Run: `npm --prefix frontend run build`
Expected: existing layout/copy does not match requested UI.

**Step 2: Write minimal implementation**

- move logo + title + collapse button into requested layout
- rename sidebar/system copy
- simplify homepage hero and panel copy

**Step 3: Run build to verify it passes**

Run: `npm --prefix frontend run build`
Expected: PASS.

### Task 4: Knowledge-base page search/pagination/create/delete

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/pages/KnowledgeBasePage.tsx`
- Modify: `frontend/src/styles/theme.css`

**Step 1:** Use frontend build as red phase after adding the new UI and API usage.

**Step 2:** Implement:
- search box
- pagination (10 per page)
- create file flow
- delete current file flow
- format-aware field visibility for flat key-value docs

**Step 3:** Re-run `npm --prefix frontend run build` and verify pass.

### Task 5: Chunk card left pane behavior

**Files:**
- Modify: `frontend/src/components/ChunkCard.tsx`
- Modify: `frontend/src/styles/theme.css`

**Step 1:** Make left content full-height, auto-growing, non-resizable, non-scrollable.

**Step 2:** Ensure right result pane stretches to same card row height.

**Step 3:** Build frontend and verify pass.

### Task 6: Final verification

**Files:**
- Modify: `README.md`

**Step 1:** Run full backend tests.

```bash
python -m pytest -q
```

**Step 2:** Run frontend build.

```bash
npm --prefix frontend run build
```

**Step 3:** Run smoke tests for:
- knowledge-base listing/read/create/delete
- logo asset access
- existing document compare flow
