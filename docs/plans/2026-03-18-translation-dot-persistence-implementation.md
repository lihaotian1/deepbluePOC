# Translation Dot Persistence Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Keep the static translation-success indicator visible after users toggle back to original text.

**Architecture:** Reuse the existing cached translation state and only adjust the view derivation logic. Add a failing state test first, then make the minimal state change needed to keep the dot visible whenever a current translation cache exists.

**Tech Stack:** TypeScript, React, Node `node:test`.

---

### Task 1: Add failing state test

**Files:**
- Modify: `frontend/tests/chunkCardTranslationState.test.ts`
- Use: `frontend/src/components/chunkCardTranslationState.ts`

**Step 1: Write the failing test**

Change the toggle-back expectation so the static dot remains visible in original-text mode after a successful translation.

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/chunkCardTranslationState.test.ts`
Expected: FAIL because the current view logic hides the dot when `isShowingTranslation` is false.

**Step 3: Write minimal implementation**

Update the translation view derivation so cached translations keep `statusDotMode: "ready"` regardless of whether the translated text is currently shown.

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/chunkCardTranslationState.test.ts`
Expected: PASS.

### Task 2: Verify and ship

**Files:**
- Modify: `frontend/src/components/chunkCardTranslationState.ts`
- Modify: `frontend/tests/chunkCardTranslationState.test.ts`

**Step 1: Run focused tests**

Run: `node --test frontend/tests/chunkCardTranslationState.test.ts`

**Step 2: Run broader frontend verification**

Run: `node --test frontend/tests/homePageCompareState.test.ts frontend/tests/streamCompare.test.ts frontend/tests/chunkCardTranslationState.test.ts`

**Step 3: Run frontend build verification**

Run: `npm --prefix frontend run build`

**Step 4: Commit**

```bash
git add frontend/src/components/chunkCardTranslationState.ts frontend/tests/chunkCardTranslationState.test.ts docs/plans/2026-03-18-translation-dot-persistence-design.md docs/plans/2026-03-18-translation-dot-persistence-implementation.md
git commit -m "fix: keep translation status dot after toggling original text"
```
