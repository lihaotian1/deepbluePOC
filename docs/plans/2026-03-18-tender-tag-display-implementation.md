# Tender Tag Display Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the compare summary display only final hit tags so tender chunks do not show extra category labels.

**Architecture:** Add a focused failing test around summary tag derivation, then make the smallest possible UI change so the summary area renders only deduplicated final `type_code` values. Do not change compare data structures or matching logic.

**Tech Stack:** TypeScript, React, Node `node:test`.

---

### Task 1: Add failing summary-tag test

**Files:**
- Create: `frontend/tests/chunkCardSummaryTags.test.ts`
- Use: `frontend/src/components/ChunkCard.tsx`

**Step 1: Write the failing test**

Add a minimal pure test that models a tender result containing:

- two matches with `type_code: 非强制-报价参考`
- three category candidates including `强制-必须偏离`, `强制-澄清`, `非强制-报价参考`

Assert that the derived summary tags contain only `非强制-报价参考` once.

**Step 2: Run test to verify it fails**

Run: `node --test frontend/tests/chunkCardSummaryTags.test.ts`
Expected: FAIL because the current summary logic still includes category chips.

**Step 3: Write minimal implementation**

Update the summary rendering logic so it derives visible tags only from final hit type codes.

**Step 4: Run test to verify it passes**

Run: `node --test frontend/tests/chunkCardSummaryTags.test.ts`
Expected: PASS.

### Task 2: Verify and ship

**Files:**
- Modify: `frontend/src/components/ChunkCard.tsx`
- Create or Modify: `frontend/tests/chunkCardSummaryTags.test.ts`

**Step 1: Run focused tests**

Run: `node --test frontend/tests/chunkCardSummaryTags.test.ts`

**Step 2: Run broader frontend verification**

Run: `node --test frontend/tests/homePageCompareState.test.ts frontend/tests/streamCompare.test.ts frontend/tests/chunkCardTranslationState.test.ts frontend/tests/chunkCardSummaryTags.test.ts`

**Step 3: Run frontend build verification**

Run: `npm --prefix frontend run build`

**Step 4: Commit**

```bash
git add frontend/src/components/ChunkCard.tsx frontend/tests/chunkCardSummaryTags.test.ts docs/plans/2026-03-18-tender-tag-display-design.md docs/plans/2026-03-18-tender-tag-display-implementation.md
git commit -m "fix: show only final tender hit tags"
```
