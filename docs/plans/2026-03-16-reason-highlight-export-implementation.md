# Reason Highlight And Export Iteration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add reason-click source-sentence highlighting to compare cards and reshape Excel export into the requested six-column deviation report.

**Architecture:** The backend will split each chunk into indexed candidate sentences, pass those sentences to the item-matching prompt, and persist validated evidence metadata on each returned match item. The frontend will use that metadata to make `item.reason` clickable and highlight a single corresponding source sentence within the same card, while the export service writes one business-facing row per match or one `OTHER` row for unmatched chunks.

**Tech Stack:** React 18, TypeScript, Vite, Node `node:test`, FastAPI, Pydantic, pytest, openpyxl.

---

### Task 1: Export workbook contract tests

**Files:**
- Modify: `backend/tests/test_export_service.py`
- Use: `backend/app/services/export_service.py`

**Step 1: Write the failing test**

Add tests that assert:
- the first sheet headers are exactly `序号`, `询价文件章节标题`, `询价文件章节原文`, `标准偏差类型`, `标准偏差原文`, `标准偏差分类`
- one matched chunk with one `MatchItem` exports one populated business row
- one unmatched chunk exports one row with blank deviation type/source and `OTHER` in the classification column

**Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_export_service.py -q`
Expected: FAIL because the workbook still uses the old technical columns and summary sheet.

**Step 3: Write minimal implementation**

Update `build_export_workbook(...)` so it writes the requested six-column rows and preserves unmatched chunks as `OTHER` rows.

**Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_export_service.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/tests/test_export_service.py backend/app/services/export_service.py
git commit -m "feat: reshape export workbook for deviation review"
```

### Task 2: Backend evidence contract tests

**Files:**
- Modify: `backend/tests/test_compare_stream_api.py`
- Modify: `backend/tests/test_matcher_logic.py`
- Use: `backend/app/schemas.py`
- Use: `backend/app/services/matcher_service.py`

**Step 1: Write the failing test**

Add tests that assert:
- streamed `chunk_result` payloads can include `evidence_sentence_index` and `evidence_sentence_text`
- matcher logic preserves valid evidence metadata on each `MatchItem`
- invalid or out-of-range evidence indices are sanitized instead of crashing

**Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_compare_stream_api.py backend/tests/test_matcher_logic.py -q`
Expected: FAIL because `MatchItem` and matcher output do not yet support evidence fields.

**Step 3: Write minimal implementation**

Extend `MatchItem` in `backend/app/schemas.py` with:

```python
evidence_sentence_index: int | None = None
evidence_sentence_text: str = ""
```

Then update matcher code paths to accept and emit those fields.

**Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_compare_stream_api.py backend/tests/test_matcher_logic.py -q`
Expected: PASS or partial progress toward PASS once parsing and sanitization are wired.

**Step 5: Commit**

```bash
git add backend/tests/test_compare_stream_api.py backend/tests/test_matcher_logic.py backend/app/schemas.py backend/app/services/matcher_service.py
git commit -m "feat: add evidence metadata to compare matches"
```

### Task 3: Prompt and LLM parsing for indexed evidence sentences

**Files:**
- Modify: `backend/app/services/prompt_builder.py`
- Modify: `backend/app/services/llm_client.py`
- Modify: `backend/tests/test_matcher_logic.py`

**Step 1: Write the failing test**

Add assertions that the batch item-matching prompt requires model output in this shape:

```json
{
  "results": [
    {
      "chunk_id": 1,
      "matches": [
        {
          "entry_id": "分类A-1",
          "reason": "原文描述与标准要求一致",
          "evidence_sentence_index": 0,
          "evidence_sentence_text": "Optional vibration detectors wired to an auxiliary conduit box"
        }
      ]
    }
  ]
}
```

Also assert that the prompt payload includes per-chunk sentence lists such as:

```json
"sentences": [
  {"index": 0, "text": "First sentence."},
  {"index": 1, "text": "Second sentence."}
]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_matcher_logic.py -q`
Expected: FAIL because prompts and parser still only know about `entry_id` and `reason`.

**Step 3: Write minimal implementation**

Update:
- `build_batch_item_messages(...)` to accept sentence metadata and require evidence fields
- `OpenAICompatibleMatcherLLM.match_items_batch(...)` to parse and normalize those fields

**Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_matcher_logic.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/services/prompt_builder.py backend/app/services/llm_client.py backend/tests/test_matcher_logic.py
git commit -m "feat: request indexed evidence sentences from matcher llm"
```

### Task 4: Sentence splitting and evidence validation in matcher service

**Files:**
- Modify: `backend/app/services/matcher_service.py`
- Modify: `backend/tests/test_matcher_logic.py`

**Step 1: Write the failing test**

Add tests that prove:
- chunk text is split into indexed sentences before item matching
- the matcher forwards sentence lists into the LLM batch call
- when the model returns an invalid index, the matcher clears the index and keeps the evidence text as fallback
- when the model returns a valid index but empty evidence text, the matcher fills the text from the local sentence list

**Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_matcher_logic.py -q`
Expected: FAIL because no sentence splitting or validation exists yet.

**Step 3: Write minimal implementation**

Implement a small helper in `backend/app/services/matcher_service.py` that splits chunk content by common Chinese/English sentence endings, line breaks, and semicolons, while keeping non-empty normalized sentence text. Use the resulting sentence list when calling the batch item matcher and when validating returned evidence metadata.

**Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_matcher_logic.py backend/tests/test_compare_stream_api.py -q`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/services/matcher_service.py backend/tests/test_matcher_logic.py backend/tests/test_compare_stream_api.py
git commit -m "feat: validate sentence evidence for compare matches"
```

### Task 5: Frontend reason-click highlight tests

**Files:**
- Create: `frontend/tests/chunkCardReasonHighlight.test.tsx`
- Use: `frontend/src/components/ChunkCard.tsx`
- Use: `frontend/src/types.ts`

**Step 1: Write the failing test**

Add tests that assert:
- clicking a rendered `item.reason` highlights exactly one source sentence
- clicking the same reason again clears the highlight
- a reason without usable evidence metadata does not activate highlighting

Use a realistic chunk such as:

```ts
const chunk = {
  chunk_id: 1,
  source: "demo.pdf",
  heading: "6.1 SUPPLY INCLUSIONS",
  level: 2,
  line_no: 1,
  content: "Pump shall include bearings. Optional vibration detectors wired to an auxiliary conduit box. The baseplate shall be painted.",
};
```

and a result match such as:

```ts
{
  entry_id: "Bearings-1",
  category: "轴承/轴承箱体Bearings / Bearing Housing",
  text: "可选的振动探测器远传至接线箱结构Optional vibration detectors wired to an auxiliary conduit box",
  type_code: "B",
  reason: "原文第二句明确写到可选的振动探测器远传至接线箱结构",
  evidence_sentence_index: 1,
  evidence_sentence_text: "Optional vibration detectors wired to an auxiliary conduit box.",
}
```

**Step 2: Run test to verify it fails**

Run: `node --test --experimental-strip-types frontend/tests/chunkCardReasonHighlight.test.tsx`
Expected: FAIL because the component does not yet expose clickable reasons or highlighted sentence markup.

**Step 3: Write minimal implementation**

Update frontend types and `ChunkCard.tsx` so preview mode builds a sentence view-model, renders clickable reasons, and toggles a single active sentence highlight.

**Step 4: Run test to verify it passes**

Run: `node --test --experimental-strip-types frontend/tests/chunkCardReasonHighlight.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/tests/chunkCardReasonHighlight.test.tsx frontend/src/components/ChunkCard.tsx frontend/src/types.ts
git commit -m "feat: highlight source sentences from compare reasons"
```

### Task 6: Frontend styling and integration verification

**Files:**
- Modify: `frontend/src/styles/theme.css`
- Modify: `frontend/src/components/ChunkCard.tsx`
- Use: `frontend/tests/chunkCardReasonHighlight.test.tsx`

**Step 1:** Use Task 5 tests as the red/green foundation.

**Step 2:** Add styles for:
- clickable reason affordance
- disabled/non-clickable reason display when no evidence exists
- active highlighted sentence appearance in the left source panel

**Step 3:** Run focused frontend verification.

Run:
- `node --test --experimental-strip-types frontend/tests/chunkCardReasonHighlight.test.tsx frontend/tests/chunkCardLayout.test.ts frontend/tests/textareaAutosize.test.ts frontend/tests/knowledgeBasePagination.test.ts frontend/tests/knowledgeBaseEditor.test.ts frontend/tests/appMainScrollReset.test.ts`
- `npm --prefix frontend run build`

Expected: PASS.

**Step 4: Commit**

```bash
git add frontend/src/styles/theme.css frontend/src/components/ChunkCard.tsx frontend/tests/chunkCardReasonHighlight.test.tsx
git commit -m "style: polish reason highlight review states"
```

### Task 7: Final verification

**Files:**
- No additional files required

**Step 1:** Run focused backend verification.

```bash
python -m pytest backend/tests/test_export_service.py backend/tests/test_compare_stream_api.py backend/tests/test_matcher_logic.py -q
```

**Step 2:** Run focused frontend verification.

```bash
node --test --experimental-strip-types frontend/tests/chunkCardReasonHighlight.test.tsx frontend/tests/chunkCardLayout.test.ts frontend/tests/textareaAutosize.test.ts frontend/tests/knowledgeBasePagination.test.ts frontend/tests/knowledgeBaseEditor.test.ts frontend/tests/appMainScrollReset.test.ts
```

**Step 3:** Run broader verification.

```bash
python -m pytest -q
npm --prefix frontend run build
```

**Step 4:** Manually verify in code that:
- `MatchItem` carries evidence metadata end-to-end
- only `item.reason` is clickable for highlight behavior
- clicking a reason highlights the matching source sentence in the same card
- export headers and rows match the requested business format

Expected: all commands pass and the affected code paths reflect the requested behavior.
