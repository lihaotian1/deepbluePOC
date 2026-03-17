# Homepage Card And Splitter Iteration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rework homepage compare-card collapsed/expanded behavior, remove the extra title numbering prefix, and make upload-time chapter splitting use GPT first with a rule-based fallback and stronger heading detection.

**Architecture:** The frontend card will move from clamp-based rendering to an explicit collapsed/expanded layout model with measured synchronized panel heights. The backend upload flow will switch from engineering-only splitting to GPT-first splitting with guarded fallback, while `chapter_splitter.py` gets both stronger heading candidate detection and stricter GPT leaf-selection instructions.

**Tech Stack:** React 18, TypeScript, Vite, Node `node:test`, FastAPI, pytest, existing chapter splitter module.

---

### Task 1: Frontend card state helper tests

**Files:**
- Create: `frontend/src/components/chunkCardLayout.ts`
- Create: `frontend/tests/chunkCardLayout.test.ts`

**Step 1: Write the failing test**

Add tests for:
- collapsed state returns tags-only view metadata
- title formatting removes the frontend-added numeric prefix and keeps the original heading text
- expanded-state synchronized height resolves to the larger of left full content height and right detail height
- collapsed-state minimum height uses a three-tag-row floor

**Step 2: Run test to verify it fails**

Run: `node --test --experimental-strip-types frontend/tests/chunkCardLayout.test.ts`
Expected: FAIL because the helper module does not exist yet.

**Step 3: Write minimal implementation**

Implement a small pure helper module so the card rendering rules are testable without DOM rendering.

**Step 4: Run test to verify it passes**

Run: `node --test --experimental-strip-types frontend/tests/chunkCardLayout.test.ts`
Expected: PASS.

### Task 2: Homepage card rendering and synchronized heights

**Files:**
- Modify: `frontend/src/components/ChunkCard.tsx`
- Modify: `frontend/src/styles/theme.css`
- Use: `frontend/src/components/chunkCardLayout.ts`

**Step 1:** Use Task 1 tests as the red foundation.

**Step 2:** Update `ChunkCard.tsx` so:
- visible title is `chunk.heading`
- collapsed mode shows only tag/status content on the right
- expanded mode shows detailed result content on the right
- left panel truncates with ellipsis when collapsed
- expanded card height becomes the max of left full content height and right detail height

**Step 3:** Update `theme.css` for the new tag-only collapsed state, synchronized panel sizing, and ellipsis/truncation presentation.

**Step 4:** Run frontend tests and build.

Run:
- `node --test --experimental-strip-types frontend/tests/chunkCardLayout.test.ts frontend/tests/textareaAutosize.test.ts frontend/tests/knowledgeBasePagination.test.ts frontend/tests/knowledgeBaseEditor.test.ts frontend/tests/appMainScrollReset.test.ts`
- `npm --prefix frontend run build`

Expected: PASS.

### Task 3: Splitter regression tests first

**Files:**
- Modify: `tests/test_chapter_splitter.py`
- Modify: `backend/tests/test_document_api.py`

**Step 1: Write the failing test**

Add tests for:
- GPT-first upload splitting path with fallback to engineering split if GPT fails
- prompt/messages include the stricter “do not skip existing intermediate headings” instruction
- a heading sequence containing `1.7`, `1.8`, `1.9` preserves `1.8` when it exists in the candidates

**Step 2: Run test to verify it fails**

Run:
- `python -m pytest tests/test_chapter_splitter.py backend/tests/test_document_api.py -q`

Expected: FAIL because upload currently uses engineering-only splitting and the GPT builder/integration is not strict enough yet.

### Task 4: GPT-first upload splitting with config-aware fallback

**Files:**
- Modify: `backend/app/config.py`
- Modify: `backend/app/main.py`
- Modify: `backend/app/api/deps.py` if needed
- Modify: `backend/app/services/splitter_service.py`
- Modify: `backend/app/api/document_routes.py` only if dependency wiring requires it

**Step 1:** Use Task 3 tests as red.

**Step 2:** Update splitter service to receive configured LLM/base-url settings and try GPT splitting first, then fall back to engineering split on any invalid or failed GPT result.

**Step 3:** Keep the upload API contract unchanged.

**Step 4:** Re-run Task 3 tests and verify improved progress.

### Task 5: Stronger chapter candidate detection and GPT prompt

**Files:**
- Modify: `chapter_splitter.py`
- Modify: `tests/test_chapter_splitter.py`

**Step 1:** Use Task 3 tests as red.

**Step 2:** Improve heading detection for realistic numeric section formatting and strengthen GPT prompt/validation so it treats existing intermediate headings as mandatory candidates instead of skipping them.

**Step 3:** Re-run:
- `python -m pytest tests/test_chapter_splitter.py backend/tests/test_document_api.py -q`

Expected: PASS.

### Task 6: Final verification

**Files:**
- No additional files required

**Step 1:** Run focused frontend tests.

```bash
node --test --experimental-strip-types frontend/tests/chunkCardLayout.test.ts frontend/tests/textareaAutosize.test.ts frontend/tests/knowledgeBasePagination.test.ts frontend/tests/knowledgeBaseEditor.test.ts frontend/tests/appMainScrollReset.test.ts
```

**Step 2:** Run focused backend tests.

```bash
python -m pytest tests/test_chapter_splitter.py backend/tests/test_document_api.py -q
```

**Step 3:** Run broader verification.

```bash
python -m pytest -q
npm --prefix frontend run build
```

**Step 4:** Manually verify in code that:
- `ChunkCard` title no longer prepends `chunk_id`
- collapsed cards are tag-only on the right
- expanded cards use max(left, right) height
- upload splitting now attempts GPT first with fallback

Expected: all commands pass and the affected code paths reflect the requested behavior.
