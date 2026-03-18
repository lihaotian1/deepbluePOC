# Compare Retry And Resume Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make compare streaming recover from transient failures and let users resume only unfinished work within the current uploaded-document session.

**Architecture:** The backend will store per-knowledge-base, per-chunk compare progress in the in-memory `SessionStore` and make the compare stream resumable by selecting only `pending` or `failed` chunks. The frontend will retry one interrupted SSE request automatically and preserve already completed results so both automatic and manual retries continue from saved session progress instead of clearing the run.

**Tech Stack:** React 18, TypeScript, Vite, Node `node:test`, FastAPI, Pydantic, pytest.

---

### Task 1: Backend session progress contract tests

**Files:**
- Modify: `backend/tests/test_session_store.py`
- Use: `backend/app/services/session_store.py`
- Use: `backend/app/schemas.py`

**Step 1: Write the failing test**

Add tests that assert:
- creating a session initializes compare progress for chunk ids as `pending` when a knowledge base run starts
- saving a successful chunk marks only that chunk as `succeeded` and preserves its result
- marking a chunk failed stores an error message without deleting other succeeded results
- editing chunks resets compare progress and clears saved compare results

**Step 2: Run test to verify it fails**

Run: `"D:\\soft\\python312\\python.exe" -m pytest backend/tests/test_session_store.py -q`
Expected: FAIL because the store does not yet track per-chunk compare status.

**Step 3: Write minimal implementation**

Add session-level compare progress models/helpers in `backend/app/schemas.py` and `backend/app/services/session_store.py` so the store can create, update, read, and reset per-chunk compare state.

**Step 4: Run test to verify it passes**

Run: `"D:\\soft\\python312\\python.exe" -m pytest backend/tests/test_session_store.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_session_store.py backend/app/services/session_store.py backend/app/schemas.py
git commit -m "feat: track per-chunk compare progress in session state"
```

### Task 2: Compare-stream resume tests

**Files:**
- Modify: `backend/tests/test_compare_stream_api.py`
- Use: `backend/app/api/compare_routes.py`
- Use: `backend/app/services/session_store.py`

**Step 1: Write the failing test**

Add API tests that assert:
- a second compare request only emits `chunk_start` for previously failed or pending chunk ids
- already succeeded chunk ids are skipped on resume
- `compare_done` includes counts for total, succeeded, failed, and skipped chunks per knowledge base or run summary

Use a fake LLM that succeeds for one chunk and fails for another on the first request, then succeeds for the failed chunk on the second request.

**Step 2: Run test to verify it fails**

Run: `"D:\\soft\\python312\\python.exe" -m pytest backend/tests/test_compare_stream_api.py -q`
Expected: FAIL because the endpoint currently reruns all chunks every time and emits only the old summary shape.

**Step 3: Write minimal implementation**

Update `backend/app/api/compare_routes.py` so it pulls resumable chunk lists from the store, skips already-succeeded chunks, and emits completion summaries that describe what was resumed.

**Step 4: Run test to verify it passes**

Run: `"D:\\soft\\python312\\python.exe" -m pytest backend/tests/test_compare_stream_api.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_compare_stream_api.py backend/app/api/compare_routes.py backend/app/services/session_store.py backend/app/schemas.py
git commit -m "feat: resume compare runs from saved chunk progress"
```

### Task 3: Backend automatic retry tests

**Files:**
- Modify: `backend/tests/test_compare_stream_api.py`
- Use: `backend/app/api/compare_routes.py`

**Step 1: Write the failing test**

Add a test that forces a batch-level compare failure on the first attempt and success on the second attempt, then assert:
- the backend retries that batch exactly once
- the final chunk result is emitted as successful
- chunks are marked `failed` only after the retry is exhausted

**Step 2: Run test to verify it fails**

Run: `"D:\\soft\\python312\\python.exe" -m pytest backend/tests/test_compare_stream_api.py -q`
Expected: FAIL because the route currently marks the whole batch as failed immediately with no retry.

**Step 3: Write minimal implementation**

Implement a small retry wrapper inside `backend/app/api/compare_routes.py` around `matcher.compare_chunks_with_trace(...)` so each failing batch gets one additional attempt before the route emits error events and stores `failed` chunk state.

**Step 4: Run test to verify it passes**

Run: `"D:\\soft\\python312\\python.exe" -m pytest backend/tests/test_compare_stream_api.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_compare_stream_api.py backend/app/api/compare_routes.py
git commit -m "feat: retry failed compare batches once"
```

### Task 4: Frontend SSE retry tests

**Files:**
- Create: `frontend/tests/streamCompare.test.ts`
- Use: `frontend/src/api/sse.ts`

**Step 1: Write the failing test**

Add tests that assert:
- a transport-level failure triggers exactly one automatic retry
- the promise resolves when the second attempt succeeds
- the promise rejects after the retry budget is exhausted
- retry notifications can be surfaced to the caller without duplicating parsed events

Mock the event-source dependency at the module boundary instead of testing the real network stack.

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/streamCompare.test.ts`
Expected: FAIL because `streamCompare(...)` currently throws immediately on the first transport error.

**Step 3: Write minimal implementation**

Refactor `frontend/src/api/sse.ts` to wrap `fetchEventSource(...)` in one explicit retry attempt and expose lightweight retry status callbacks/messages back to the caller.

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/streamCompare.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/tests/streamCompare.test.ts frontend/src/api/sse.ts
git commit -m "feat: retry interrupted compare streams once"
```

### Task 5: Frontend resume-state tests

**Files:**
- Modify: `frontend/tests/homePageCompareState.test.ts`
- Modify: `frontend/tests/knowledgeBaseEditor.test.ts`
- Use: `frontend/src/pages/HomePage.tsx`
- Use: `frontend/src/pages/homePageCompareState.ts`
- Use: `frontend/src/types.ts`

**Step 1: Write the failing test**

Add tests that assert:
- starting a retry run does not clear already completed results for a knowledge base
- incoming chunk results merge into the existing per-knowledge-base result map
- editing chunk content still clears stale compare results and resets the active filter

If direct `HomePage.tsx` testing is awkward, extract minimal pure helpers into `homePageCompareState.ts` and test them there.

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/homePageCompareState.test.ts`
Expected: FAIL because the current compare flow assumes a full rerun and clears results at the start.

**Step 3: Write minimal implementation**

Add small state helpers in `frontend/src/pages/homePageCompareState.ts` for preserving existing results across retries while keeping edit invalidation strict. Update `frontend/src/pages/HomePage.tsx` to use them.

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/homePageCompareState.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/tests/homePageCompareState.test.ts frontend/src/pages/homePageCompareState.ts frontend/src/pages/HomePage.tsx
git commit -m "feat: preserve completed compare results during resume"
```

### Task 6: End-to-end resume UX wiring

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/components/ComparePanel.tsx`
- Use: `frontend/src/api/sse.ts`
- Use: `backend/app/api/compare_routes.py`

**Step 1: Use Task 4 and Task 5 tests as the red/green foundation.**

**Step 2: Write minimal implementation**

Update the compare UI flow so it:
- logs when an automatic retry starts
- tells the user that a manual click will resume only failed or pending chunks
- shows completion text that reflects resumed/skipped work instead of implying every run was a fresh full compare

Keep the UI simple; do not add new pages or complex retry dashboards.

**Step 3: Run focused tests**

Run: `node --test frontend/tests/streamCompare.test.ts frontend/tests/homePageCompareState.test.ts`
Expected: PASS.

**Step 4: Run broader verification**

Run: `"D:\\soft\\python312\\python.exe" -m pytest backend/tests/test_session_store.py backend/tests/test_compare_stream_api.py -q && node --test frontend/tests/*.test.ts && npm run build`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/pages/HomePage.tsx frontend/src/components/ComparePanel.tsx frontend/src/api/sse.ts frontend/src/pages/homePageCompareState.ts frontend/tests/streamCompare.test.ts frontend/tests/homePageCompareState.test.ts backend/app/api/compare_routes.py backend/app/services/session_store.py backend/app/schemas.py backend/tests/test_session_store.py backend/tests/test_compare_stream_api.py
git commit -m "feat: add resumable compare retries"
```
