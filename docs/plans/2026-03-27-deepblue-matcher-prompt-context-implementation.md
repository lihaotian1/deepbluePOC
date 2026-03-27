# DeepBlue Matcher Prompt Context Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add DeepBlue business-context guidance to classification and item-matching prompts, including representative category samples during classification.

**Architecture:** `MatcherService` will derive compact category sample contexts from the loaded knowledge base and pass them into the classification prompt builders through `OpenAICompatibleMatcherLLM`. `prompt_builder.py` will own the revised prompt wording and JSON payload shape, while existing response parsing in `llm_client.py` continues validating IDs and structured outputs.

**Tech Stack:** Python 3, FastAPI services, Pydantic, pytest.

---

### Task 1: Prompt-builder classification tests

**Files:**
- Modify: `backend/tests/test_matcher_logic.py`
- Modify: `backend/app/services/prompt_builder.py`

**Step 1: Write the failing test**

Add tests that assert batch classification prompts:
- describe `chunks` as inquiry requirements for DeepBlue
- describe category contexts as DeepBlue-provided capability content
- include `category_contexts` with representative sample entries

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_matcher_logic.py -k prompt`
Expected: FAIL because the current classification payload and wording do not include the new business context.

**Step 3: Write minimal implementation**

Add classification prompt wording and payload fields needed to satisfy the new tests.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_matcher_logic.py -k prompt`
Expected: PASS.

### Task 2: Matcher-service category sample wiring

**Files:**
- Modify: `backend/tests/test_matcher_logic.py`
- Modify: `backend/app/services/matcher_service.py`
- Modify: `backend/app/services/llm_client.py`

**Step 1: Write the failing test**

Add a matcher-service or LLM-call test asserting batch classification receives representative category sample contexts derived from the knowledge base.

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_matcher_logic.py -k category_context`
Expected: FAIL because the matcher currently forwards only raw category keys.

**Step 3: Write minimal implementation**

Build small per-category sample payloads in `MatcherService` and thread them through `OpenAICompatibleMatcherLLM.classify_categories_batch`.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_matcher_logic.py -k category_context`
Expected: PASS.

### Task 3: Item-matching prompt context refresh

**Files:**
- Modify: `backend/tests/test_matcher_logic.py`
- Modify: `backend/app/services/prompt_builder.py`

**Step 1: Write the failing test**

Add assertions that the item-matching prompt explains `chunks` as inquiry requirements and `candidates` as DeepBlue-provided content used to satisfy them.

**Step 2: Run test to verify it fails**

Run: `pytest backend/tests/test_matcher_logic.py -k item_prompt`
Expected: FAIL because the current prompt only mentions generic semantic matching.

**Step 3: Write minimal implementation**

Revise the item-matching wording while preserving JSON schema and evidence constraints.

**Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_matcher_logic.py -k item_prompt`
Expected: PASS.

### Task 4: Final backend verification

**Files:**
- Use: `backend/tests/test_matcher_logic.py`
- Use: `backend/tests/test_compare_stream_api.py`

**Step 1: Run focused matcher tests**

Run: `pytest backend/tests/test_matcher_logic.py`
Expected: PASS.

**Step 2: Run compare-stream regression tests**

Run: `pytest backend/tests/test_compare_stream_api.py`
Expected: PASS.

**Step 3: Commit**

```bash
git add docs/plans/2026-03-27-deepblue-matcher-prompt-context-design.md docs/plans/2026-03-27-deepblue-matcher-prompt-context-implementation.md backend/app/services/prompt_builder.py backend/app/services/llm_client.py backend/app/services/matcher_service.py backend/tests/test_matcher_logic.py
git commit -m "feat: clarify deepblue matcher prompt context"
```
