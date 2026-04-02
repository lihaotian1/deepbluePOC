# Prompt Match Decision Criteria Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Teach the matcher prompts to rank strong association, conditional support, and conflict explicitly instead of relying on generic semantic similarity.

**Architecture:** `prompt_builder.py` remains the single source of truth for classification and item-matching instructions. Tests in `backend/tests/test_matcher_logic.py` lock the new decision criteria wording so the LLM contract can evolve without changing the JSON schema or parser logic.

**Tech Stack:** Python 3, pytest, FastAPI backend services.

---

### Task 1: Prompt regression tests

**Files:**
- Modify: `backend/tests/test_matcher_logic.py`
- Modify: `backend/app/services/prompt_builder.py`

**Step 1: Write the failing test**

Add tests asserting prompt text now includes:
- strong association / same object / same constraint guidance
- strong association but conflict can still be returned
- topic-only similarity should be excluded

**Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_matcher_logic.py -k "decision_criteria or theme_only or conflict"`
Expected: FAIL because the current prompt wording does not include the new ranking rules.

**Step 3: Write minimal implementation**

Update the classification and item-matching prompts plus `rule` text to encode the new decision criteria and `reason` expectations.

**Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_matcher_logic.py -k "decision_criteria or theme_only or conflict"`
Expected: PASS.

### Task 2: Broader matcher verification

**Files:**
- Use: `backend/tests/test_matcher_logic.py`
- Use: `backend/tests/test_compare_stream_api.py`

**Step 1: Run focused matcher tests**

Run: `python -m pytest backend/tests/test_matcher_logic.py`
Expected: PASS.

**Step 2: Run compare-stream regression tests**

Run: `python -m pytest backend/tests/test_compare_stream_api.py`
Expected: PASS.
