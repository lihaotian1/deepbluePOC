# Smart Analysis Copy Refresh Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace user-visible analysis workflow wording from `比对` to `智能分析` and add a compact progress bar to the analysis-panel status row.

**Architecture:** `HomePage.tsx` keeps the streaming-derived progress numbers alongside the existing status text and passes them into `ComparePanel.tsx`. The compare panel stays presentation-focused, while `comparePanelViewState.ts` owns button-copy and progress-fill helpers so the behavior remains testable without rendering React.

**Tech Stack:** React 18, TypeScript, Vite, Node `node:test`.

---

### Task 1: Compare-panel copy and progress view state

**Files:**
- Modify: `frontend/tests/comparePanelViewState.test.ts`
- Modify: `frontend/src/components/comparePanelViewState.ts`

**Step 1: Write the failing test**

Add tests that assert:
- the primary action button reads `开始智能分析` when idle and `智能分析中...` while running
- a progress helper returns `0` for unknown totals, the expected percentage for active runs, and `100` when current reaches total

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/comparePanelViewState.test.ts`
Expected: FAIL because the old wording and progress helper behavior do not exist yet.

**Step 3: Write minimal implementation**

Update the compare-panel action-button copy and add a small helper for deriving progress-bar fill percentages.

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/comparePanelViewState.test.ts`
Expected: PASS.

### Task 2: Homepage copy refresh and analysis progress state

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/components/ChunkCard.tsx`
- Use: `frontend/src/components/comparePanelViewState.ts`
- Use: `frontend/src/pages/homePageReviewState.ts`

**Step 1: Use Task 1 as the red/green foundation.**

**Step 2: Write minimal implementation**

Add structured progress state to `HomePage.tsx`, update visible status/log strings from `比对` to `智能分析`, reset progress numbers across upload/run completion/failure, and update chunk-card user-facing hints to use the new wording.

**Step 3: Run focused tests**

Run: `node --test frontend/tests/comparePanelViewState.test.ts frontend/tests/homePageReviewState.test.ts`
Expected: PASS.

### Task 3: Analysis-panel progress bar UI

**Files:**
- Modify: `frontend/src/components/ComparePanel.tsx`
- Modify: `frontend/src/styles/theme.css`
- Use: `frontend/src/components/comparePanelViewState.ts`

**Step 1: Write the failing test**

Extend `frontend/tests/comparePanelViewState.test.ts` only if an additional pure helper is needed for bar fill behavior.

**Step 2: Write minimal implementation**

Pass progress numbers into `ComparePanel.tsx`, render a compact progress track beside the status dot, and add the CSS needed for the narrow bar while leaving chunk-card translation dots unchanged.

**Step 3: Run focused tests**

Run: `node --test frontend/tests/comparePanelViewState.test.ts frontend/tests/homePageReviewState.test.ts`
Expected: PASS.

**Step 4: Run build verification**

Run: `npm --prefix frontend run build`
Expected: PASS.

### Task 4: Final verification

**Files:**
- Use: `frontend/tests/comparePanelViewState.test.ts`
- Use: `frontend/tests/homePageReviewState.test.ts`

**Step 1: Run frontend tests**

Run: `node --test frontend/tests/comparePanelViewState.test.ts frontend/tests/homePageReviewState.test.ts`
Expected: PASS.

**Step 2: Run build verification**

Run: `npm --prefix frontend run build`
Expected: PASS.
