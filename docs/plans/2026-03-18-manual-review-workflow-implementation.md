# Manual Review Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add homepage manual review controls, modal-based hit adjustment, review submission display, and Excel export of review status.

**Architecture:** The backend keeps reviewed compare results and document submission state inside the existing session store so export can use one canonical snapshot. The frontend updates that snapshot through focused review-state helpers, chunk-card review dialogs, and a compare-toolbar submission control while preserving the current compare and chunk-edit flows.

**Tech Stack:** React 18, TypeScript, Vite, Node `node:test`, FastAPI, Pydantic, pytest, openpyxl.

---

### Task 1: Backend review persistence contract

**Files:**
- Modify: `backend/tests/test_document_api.py`
- Modify: `backend/tests/test_session_store.py`
- Modify: `backend/app/schemas.py`
- Modify: `backend/app/services/session_store.py`
- Modify: `backend/app/api/document_routes.py`

**Step 1: Write the failing test**

Add tests that assert:
- `PUT /api/v1/documents/{doc_id}/review` stores reviewed compare results and `submitted_for_review`
- session review persistence keeps knowledge-base results separated per file
- updating chunk content still clears compare results and submission state

**Step 2: Run test to verify it fails**

Run: `"D:\soft\python312\python.exe" -m pytest backend/tests/test_document_api.py backend/tests/test_session_store.py -q`
Expected: FAIL because the review endpoint and session fields do not exist yet.

**Step 3: Write minimal implementation**

Add review request/response models, session fields, and a review-save route that replaces the stored reviewed snapshot.

**Step 4: Run test to verify it passes**

Run: `"D:\soft\python312\python.exe" -m pytest backend/tests/test_document_api.py backend/tests/test_session_store.py -q`
Expected: PASS.

### Task 2: Backend export review column

**Files:**
- Modify: `backend/tests/test_export_service.py`
- Modify: `backend/app/services/export_service.py`
- Use: `backend/app/schemas.py`

**Step 1: Write the failing test**

Add tests that assert:
- the workbook headers end with `审核状态`
- matched and unmatched rows both export the correct review status
- manually edited rows still export the stored `reason` and row text

**Step 2: Run test to verify it fails**

Run: `"D:\soft\python312\python.exe" -m pytest backend/tests/test_export_service.py -q`
Expected: FAIL because the export service does not emit review status yet.

**Step 3: Write minimal implementation**

Append `审核状态` to exported headers and include the chunk result's `review_status` on every exported row.

**Step 4: Run test to verify it passes**

Run: `"D:\soft\python312\python.exe" -m pytest backend/tests/test_export_service.py -q`
Expected: PASS.

### Task 3: Frontend review-state helpers

**Files:**
- Create: `frontend/src/pages/homePageReviewState.ts`
- Create: `frontend/tests/homePageReviewState.test.ts`
- Modify: `frontend/src/types.ts`

**Step 1: Write the failing test**

Add pure-state tests that assert:
- compare results default to `未审`
- marking a chunk reviewed sets `已审`
- editing reason, deleting a row, or adding a row resets the chunk to `未审`
- deleting the last row turns the chunk into `其他`
- adding an `其他` row uses `未命中知识库条目，归类为其他。`

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/homePageReviewState.test.ts`
Expected: FAIL because the helper module does not exist yet.

**Step 3: Write minimal implementation**

Create focused helper functions for reviewed result normalization and manual row mutations.

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/homePageReviewState.test.ts`
Expected: PASS.

### Task 4: Homepage review persistence wiring

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/components/ComparePanel.tsx`
- Use: `frontend/src/pages/homePageReviewState.ts`

**Step 1: Use Task 3 tests as the red/green foundation.**

**Step 2: Write minimal implementation**

Add the review-save API helper, document submission state, and compare/export submission flow so reviewed results are saved before export and after submission confirmation.

**Step 3: Run focused tests**

Run: `node --test frontend/tests/homePageReviewState.test.ts frontend/tests/homePageCompareState.test.ts`
Expected: PASS.

### Task 5: Chunk-card review UI and dialogs

**Files:**
- Modify: `frontend/src/components/ChunkCard.tsx`
- Modify: `frontend/src/styles/theme.css`
- Use: `frontend/src/api/client.ts`
- Use: `frontend/src/pages/homePageReviewState.ts`

**Step 1: Write the failing test**

Extend `frontend/tests/homePageReviewState.test.ts` only when a new pure-state helper is needed for chunk review behavior.

**Step 2: Write minimal implementation**

Update `ChunkCard` so it:
- moves `预览` / `编辑` into the source-panel header above `翻译`
- replaces header actions with `修改` / `审核`
- renders a second-level edit modal with current rows, reason editing, row removal, and add-entry launch
- renders a third-level add modal that loads the active knowledge base, lists current-file categories, supports `其他`, and requires a non-empty opinion

**Step 3: Run focused tests**

Run: `node --test frontend/tests/homePageReviewState.test.ts frontend/tests/homePageCompareState.test.ts`
Expected: PASS.

**Step 4: Run build verification**

Run: `npm --prefix frontend run build`
Expected: PASS.

### Task 6: Final verification

**Files:**
- Use: `backend/tests/test_document_api.py`
- Use: `backend/tests/test_session_store.py`
- Use: `backend/tests/test_export_service.py`
- Use: `frontend/tests/homePageReviewState.test.ts`
- Use: `frontend/tests/homePageCompareState.test.ts`

**Step 1: Run backend verification**

Run: `"D:\soft\python312\python.exe" -m pytest backend/tests/test_document_api.py backend/tests/test_session_store.py backend/tests/test_export_service.py -q`
Expected: PASS.

**Step 2: Run frontend verification**

Run: `node --test frontend/tests/homePageReviewState.test.ts frontend/tests/homePageCompareState.test.ts`
Expected: PASS.

**Step 3: Run build verification**

Run: `npm --prefix frontend run build`
Expected: PASS.
