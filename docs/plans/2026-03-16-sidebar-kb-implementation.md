# Sidebar And Knowledge Base Management Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a collapsible left sidebar with logo and page navigation, plus a structured knowledge-base management page that reads and writes JSON files under `data/知识库`.

**Architecture:** FastAPI exposes knowledge-base file listing, document read/save, and static logo access. React gains an app shell with a collapsible sidebar, a home view, and a structured knowledge-base editor view sharing the same layout.

**Tech Stack:** FastAPI, Pydantic, React, TypeScript, Vite, existing axios client, StaticFiles.

---

### Task 1: Knowledge-base backend tests

**Files:**
- Create: `backend/tests/test_knowledge_base_service.py`
- Create: `backend/tests/test_knowledge_base_api.py`

**Step 1: Write the failing test**

Add tests for:
- listing `data/知识库/*.json`
- reading a JSON file into structured category/item data
- saving edited structured data back to `{分类: [{条目: 类型}]}`
- refreshing the matcher cache when the default knowledge-base file is saved

**Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_knowledge_base_service.py backend/tests/test_knowledge_base_api.py -q`
Expected: FAIL because service and routes do not exist.

**Step 3: Write minimal implementation**

Create knowledge-base service and API route module.

**Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_knowledge_base_service.py backend/tests/test_knowledge_base_api.py -q`
Expected: PASS.

### Task 2: Backend knowledge-base service and static logo

**Files:**
- Modify: `backend/app/config.py`
- Create: `backend/app/services/knowledge_base_manager.py`
- Create: `backend/app/api/knowledge_base_routes.py`
- Modify: `backend/app/api/deps.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/main.py`

**Step 1: Write the failing test**

Use the tests from Task 1 as the red phase.

**Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_knowledge_base_service.py backend/tests/test_knowledge_base_api.py -q`

**Step 3: Write minimal implementation**

- Add knowledge-base directory config and logo directory config.
- Add manager methods `list_files`, `read_file`, `save_file`.
- Register knowledge-base CRUD routes.
- Mount logo static files.
- Refresh matcher cache after saving the configured default knowledge-base file.

**Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_knowledge_base_service.py backend/tests/test_knowledge_base_api.py -q`

### Task 3: Frontend shell and sidebar

**Files:**
- Create: `frontend/src/components/Sidebar.tsx`
- Create: `frontend/src/layouts/AppShell.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/styles/theme.css`

**Step 1: Write the failing check**

Run: `npm --prefix frontend run build`
Expected: current app has no sidebar/layout components.

**Step 2: Write minimal implementation**

- Add app shell with collapsible sidebar
- Show logo at the top
- Add `主页` and `知识库` menu items with icon-only collapsed state

**Step 3: Run check to verify it passes**

Run: `npm --prefix frontend run build`
Expected: PASS.

### Task 4: Knowledge-base page and structured CRUD editor

**Files:**
- Create: `frontend/src/pages/KnowledgeBasePage.tsx`
- Create: `frontend/src/components/KnowledgeBaseEditor.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/styles/theme.css`

**Step 1: Write the failing check**

Run: `npm --prefix frontend run build`
Expected: FAIL because knowledge-base page/client types are missing.

**Step 2: Write minimal implementation**

- Fetch knowledge-base file list
- Render submenu under `知识库`
- Load selected knowledge-base file
- Support category/item add/edit/delete in local state
- Save whole document back to backend

**Step 3: Run check to verify it passes**

Run: `npm --prefix frontend run build`
Expected: PASS.

### Task 5: Final verification

**Files:**
- Modify: `README.md`

**Step 1: Run backend tests**

Run: `python -m pytest -q`
Expected: all tests pass.

**Step 2: Run frontend build**

Run: `npm --prefix frontend run build`
Expected: build succeeds.

**Step 3: Run smoke check**

Run a lightweight FastAPI TestClient smoke test for knowledge-base read/save and existing compare flow.
