# Homepage Pagination Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add homepage pagination with duplicated top and bottom pagers, fixed 10-item pages, and a per-page reviewed counter that matches the active filter and knowledge-base view.

**Architecture:** A pure homepage pagination helper computes page clamping, current-page chunk slices, and current-page reviewed counts from the already filtered chunk list plus the active knowledge-base results. `HomePage.tsx` keeps only the page state, reset rules, and rendering of the two shared `.kb-pagination-bar` sections.

**Tech Stack:** React 18, TypeScript, Vite, Node `node:test`.

---

### Task 1: Homepage pagination helper

**Files:**
- Create: `frontend/tests/homePagePagination.test.ts`
- Create: `frontend/src/pages/homePagePagination.ts`
- Use: `frontend/src/types.ts`

**Step 1: Write the failing test**

Add tests that assert:
- the helper slices homepage chunks into 10-item pages
- the helper clamps out-of-range pages to the last available page
- the helper counts only current-page reviewed items
- the helper uses the current page's actual item count as the `已审` denominator on the final short page

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/homePagePagination.test.ts`
Expected: FAIL because the helper module does not exist yet.

**Step 3: Write minimal implementation**

Create a pure helper that returns the corrected page, current page chunks, total counts, and reviewed-count metadata.

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/homePagePagination.test.ts`
Expected: PASS.

### Task 2: Homepage pager integration

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`
- Use: `frontend/src/pages/homePagePagination.ts`
- Use: `frontend/src/pages/homePageReviewState.ts`

**Step 1: Use Task 1 as the red/green foundation.**

**Step 2: Write minimal implementation**

Add homepage `page` state, reset it on filter/result-set transitions, replace the raw `filteredChunks.map(...)` render with the paged chunk slice, and render matching top and bottom `.kb-pagination-bar` sections without the knowledge-base create button.

**Step 3: Run focused tests**

Run: `node --test frontend/tests/homePagePagination.test.ts frontend/tests/homePageReviewState.test.ts`
Expected: PASS.

**Step 4: Run build verification**

Run: `npm --prefix frontend run build`
Expected: PASS.

### Task 3: Final verification

**Files:**
- Use: `frontend/tests/homePagePagination.test.ts`
- Use: `frontend/tests/homePageReviewState.test.ts`

**Step 1: Run frontend tests**

Run: `node --test frontend/tests/homePagePagination.test.ts frontend/tests/homePageReviewState.test.ts`
Expected: PASS.

**Step 2: Run build verification**

Run: `npm --prefix frontend run build`
Expected: PASS.
