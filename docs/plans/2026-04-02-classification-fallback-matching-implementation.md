# Classification Fallback Matching Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a fallback item-matching pass for chunks that classification or initial category matching leaves without any hits.

**Architecture:** `MatcherService.compare_chunks_with_trace()` remains the orchestration point. After normal classified matching fills `match_rows`, it will perform a second pass only for zero-hit chunks against remaining categories and append any recovered matches plus trace events. No API schema changes are needed.

**Tech Stack:** Python 3, pytest, FastAPI backend services.

---

### Task 1: Matcher fallback tests

**Files:**
- Modify: `backend/tests/test_matcher_logic.py`
- Modify: `backend/app/services/matcher_service.py`

**Step 1: Write the failing test**

Add tests asserting:
- fallback recovers a hit when classification returns no categories
- fallback recovers a hit when classification picks the wrong category and the first pass returns no items
- fallback does not add extra category calls when an initial item hit already exists

**Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_matcher_logic.py -k "fallback"`
Expected: FAIL because the matcher currently never tries categories outside the classified set.

**Step 3: Write minimal implementation**

Add a fallback item-matching loop for zero-hit chunks across remaining categories and record explicit fallback trace events.

**Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_matcher_logic.py -k "fallback"`
Expected: PASS.

### Task 2: Broader backend verification

**Files:**
- Use: `backend/tests/test_matcher_logic.py`
- Use: `backend/tests/test_compare_stream_api.py`
- Use: `backend/tests/test_kb_loader.py`

**Step 1: Run matcher tests**

Run: `python -m pytest backend/tests/test_matcher_logic.py`
Expected: PASS.

**Step 2: Run compare-stream regression tests**

Run: `python -m pytest backend/tests/test_compare_stream_api.py backend/tests/test_kb_loader.py`
Expected: PASS.
