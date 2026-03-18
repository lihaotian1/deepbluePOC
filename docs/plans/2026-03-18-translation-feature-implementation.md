# Translation Feature Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a homepage per-chunk Chinese translation toggle that uses the existing backend LLM client, preserves original content, and shows animated/static `pulse-dot` status.

**Architecture:** The backend will expose a focused translation endpoint backed by the existing OpenAI-compatible LLM wrapper. The frontend will call that endpoint from each `ChunkCard`, keep translation state local to the card, cache successful translations per source snapshot, and invalidate stale translations when the source content changes.

**Tech Stack:** React 18, TypeScript, Vite, Node `node:test`, FastAPI, Pydantic, pytest.

---

### Task 1: Backend translation contract tests

**Files:**
- Create or Modify: `backend/tests/test_translation_api.py`
- Use: `backend/app/services/llm_client.py`
- Use: `backend/app/main.py`

**Step 1: Write the failing test**

Add tests that assert:
- `POST /api/v1/translate/chinese` returns `{ "translation": ... }` for valid text
- empty or blank `text` is rejected with validation failure
- backend LLM errors are surfaced as a clear non-200 response

Use a fake LLM attached to `app.state.matcher_llm` so the tests stay deterministic.

**Step 2: Run test to verify it fails**

Run: `"D:\soft\python312\python.exe" -m pytest backend/tests/test_translation_api.py -q`
Expected: FAIL because the translation route does not exist yet.

**Step 3: Write minimal implementation**

Add the route, request/response models, and the LLM client translation method needed to satisfy the new tests.

**Step 4: Run test to verify it passes**

Run: `"D:\soft\python312\python.exe" -m pytest backend/tests/test_translation_api.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_translation_api.py backend/app/api/translation_routes.py backend/app/services/llm_client.py backend/app/main.py backend/app/schemas.py
git commit -m "feat: add chinese translation api"
```

### Task 2: Frontend translation state tests

**Files:**
- Create: `frontend/src/components/chunkCardTranslationState.ts`
- Create: `frontend/tests/chunkCardTranslationState.test.ts`
- Use: `frontend/src/components/ChunkCard.tsx`

**Step 1: Write the failing test**

Add pure-state tests that assert:
- initial state shows source text with `翻译`
- starting a request sets `isTranslating` and shows an animated dot state
- a successful response switches to translated view, changes the button text to `原文`, and marks the dot static
- toggling back to original keeps the cached translation available
- changing source text invalidates the cached translation and clears any active status
- a stale async result is ignored when the source snapshot no longer matches

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/chunkCardTranslationState.test.ts`
Expected: FAIL because the helper does not exist yet.

**Step 3: Write minimal implementation**

Create a small helper module that derives button label, dot state, display text, and stale-result handling from explicit translation state transitions.

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/chunkCardTranslationState.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/components/chunkCardTranslationState.ts frontend/tests/chunkCardTranslationState.test.ts
git commit -m "feat: add chunk translation state model"
```

### Task 3: Frontend API wiring

**Files:**
- Modify: `frontend/src/api/client.ts`
- Modify: `frontend/src/types.ts`
- Use: `backend/app/api/translation_routes.py`

**Step 1: Use Task 1 backend test as the contract source.**

**Step 2: Write minimal implementation**

Add a `translateChunkContent(text)` API helper and any lightweight request/response types needed by the frontend.

**Step 3: Run focused tests**

Run: `node --test frontend/tests/chunkCardTranslationState.test.ts`
Expected: PASS; no regression from the API helper additions.

**Step 4: Commit**

```bash
git add frontend/src/api/client.ts frontend/src/types.ts
git commit -m "feat: add frontend translation client"
```

### Task 4: Chunk card translation UI

**Files:**
- Modify: `frontend/src/components/ChunkCard.tsx`
- Modify: `frontend/src/styles/theme.css`
- Use: `frontend/src/components/chunkCardTranslationState.ts`
- Use: `frontend/src/api/client.ts`

**Step 1: Use Task 2 tests as the red/green foundation.**

**Step 2: Write minimal implementation**

Update the chunk card so it:
- renders a `翻译` / `原文` toggle in the `原文内容` header
- disables the button while translation is in flight
- shows animated/static `pulse-dot` state at the correct times
- swaps the displayed text between source and cached translation without touching `chunk.content`
- clears translation state when the source content changes
- shows a lightweight inline error on translation failure

Keep the existing preview/edit behavior intact.

**Step 3: Run focused tests**

Run: `node --test frontend/tests/chunkCardTranslationState.test.ts`
Expected: PASS.

**Step 4: Run manual verification helper**

Run: `npm --prefix frontend run build`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/components/ChunkCard.tsx frontend/src/styles/theme.css frontend/src/components/chunkCardTranslationState.ts frontend/tests/chunkCardTranslationState.test.ts frontend/src/api/client.ts frontend/src/types.ts
git commit -m "feat: add chunk translation toggle"
```

### Task 5: Final verification

**Files:**
- Use: `backend/tests/test_translation_api.py`
- Use: `frontend/tests/chunkCardTranslationState.test.ts`
- Use: `frontend/src/components/ChunkCard.tsx`

**Step 1: Run backend verification**

Run: `"D:\soft\python312\python.exe" -m pytest backend/tests/test_translation_api.py -q`
Expected: PASS.

**Step 2: Run frontend verification**

Run: `node --test frontend/tests/chunkCardTranslationState.test.ts`
Expected: PASS.

**Step 3: Run build verification**

Run: `npm --prefix frontend run build`
Expected: PASS.

**Step 4: Review touched files**

Confirm only the planned backend translation files, chunk-card UI files, test files, and docs changed.

**Step 5: Commit**

```bash
git add backend/tests/test_translation_api.py backend/app/api/translation_routes.py backend/app/services/llm_client.py backend/app/main.py backend/app/schemas.py frontend/src/components/chunkCardTranslationState.ts frontend/tests/chunkCardTranslationState.test.ts frontend/src/api/client.ts frontend/src/types.ts frontend/src/components/ChunkCard.tsx frontend/src/styles/theme.css docs/plans/2026-03-18-translation-feature-design.md docs/plans/2026-03-18-translation-feature-implementation.md
git commit -m "feat: add homepage translation toggle"
```
