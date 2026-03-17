# Reason Highlight And Export Iteration Design

## Goal

Add an evidence-linked review flow where clicking the model summary reason in a compare result highlights the corresponding sentence in the source text, and update Excel export so each row matches the requested business-facing deviation columns.

## Confirmed UX Decisions

- Only `item.reason` is clickable for source highlighting.
- Clicking a reason highlights exactly one corresponding sentence in the left source panel of the same chunk card.
- The implementation uses model-returned evidence metadata, not frontend-only fuzzy guessing, as the primary source of truth.
- The model should return both an evidence sentence index and the evidence sentence text for each matched item.
- Excel export should output six business columns: sequence, chapter heading, chapter source text, deviation type, deviation source text, and deviation classification.
- Unmatched chunks should still export one row with empty deviation-type/source columns and `OTHER` in the classification column.

## Current-State Findings

### Compare result rendering

`frontend/src/components/ChunkCard.tsx` currently renders match text and reason as plain display content. The left source panel renders either truncated plain text or full `ReactMarkdown`, and there is no interaction state that can map a clicked reason back to a source sentence.

### Matcher contract

`backend/app/schemas.py` defines `MatchItem` with only `entry_id`, `category`, `text`, `type_code`, and `reason`. The batch item-matching prompt in `backend/app/services/prompt_builder.py` asks the model to return only `entry_id` and `reason`, and `backend/app/services/llm_client.py` only parses those two fields.

### Export shape

`backend/app/services/export_service.py` currently writes a technical `results` sheet with internal column names plus a second `summary` sheet. The current structure does not match the requested business export format.

## Chosen Approach

### 1. Evidence-guided highlighting with indexed source sentences

The backend will split each chunk source into a deterministic sentence list before item matching. When asking the model to match knowledge-base entries, the prompt will include the chunk content plus its candidate source sentences as indexed items. For each matched entry, the model must return:

- `entry_id`
- `reason`
- `evidence_sentence_index`
- `evidence_sentence_text`

The frontend will treat `evidence_sentence_index` as the primary key for highlighting. `evidence_sentence_text` exists as an audit/debug field and as a fallback if an index is missing or invalid.

### 2. Frontend interaction stays local to each chunk card

`ChunkCard` will own a local active-evidence state. Clicking a reason toggles the selected evidence on or off and highlights only the matching sentence in the left source panel of that card. There is no cross-card synchronization, no multi-select highlighting, and no click behavior on `item.text` in this iteration.

### 3. Controlled sentence rendering for highlightable source view

To keep sentence-level highlighting deterministic, the left source panel in preview mode will render from a sentence view-model instead of relying on post-render DOM searching inside `ReactMarkdown`. This prioritizes reliable auditing over preserving every markdown decoration in the highlighted view. The collapsed view can keep its existing truncation behavior; the expanded preview will render sentence spans and attach a highlighted style to the active one.

### 4. Excel export becomes a single business-facing results sheet

The workbook will export one primary results sheet with exactly these headers:

- `序号`
- `询价文件章节标题`
- `询价文件章节原文`
- `标准偏差类型`
- `标准偏差原文`
- `标准偏差分类`

Each matched entry produces one row. If a chunk has no matches, export one row with chapter information populated, deviation type/source blank, and classification set to `OTHER`.

### 5. Graceful fallback and validation

The backend parser will validate evidence indices returned by the model against the locally generated sentence list. If the index is not an integer or is out of range, the service will clear the index and retain the evidence text only. The frontend will only enable clickable highlighting when usable evidence metadata exists.

## Alternatives Considered

### A. Return only evidence sentence text and let the frontend search for it

Rejected as the primary design because line breaks, markdown normalization, duplicated clauses, and minor model paraphrasing would make string matching too fragile.

### B. Infer evidence locally from `item.reason` or `item.text`

Rejected because summary text is not guaranteed to mirror the source sentence closely enough for deterministic matching, and local semantic retrieval would introduce extra heuristic behavior into an audit workflow.

### C. Make both `item.text` and `item.reason` clickable

Rejected for this iteration because the requested UX is specifically reason-click highlighting, and limiting the click target keeps the interaction model simpler for reviewers.

## Component / File Impact

- `backend/app/schemas.py`
  - add evidence metadata fields to `MatchItem`
- `backend/app/services/prompt_builder.py`
  - include indexed chunk sentences in the batch item-matching prompt
  - require model output to contain evidence fields
- `backend/app/services/llm_client.py`
  - parse and sanitize evidence metadata
- `backend/app/services/matcher_service.py`
  - split chunk content into sentences before matching
  - validate and attach evidence metadata to each `MatchItem`
- `backend/app/services/export_service.py`
  - replace internal export columns with the requested business columns
  - remove or stop relying on the extra summary sheet
- `frontend/src/types.ts`
  - add evidence fields to `MatchItem`
- `frontend/src/components/ChunkCard.tsx`
  - render clickable reasons
  - manage active evidence state
  - render preview sentences with one highlighted sentence at a time
- `frontend/src/styles/theme.css`
  - add clickable reason and active-source-sentence styles
- `backend/tests/test_compare_stream_api.py`
  - assert compare-stream payloads include evidence metadata
- `backend/tests/test_export_service.py`
  - assert the new workbook shape and row expansion rules
- `frontend/tests/*`
  - add focused reason-click highlight behavior coverage

## Testing Strategy

- Backend contract tests first: prove compare results can carry evidence sentence metadata and export columns match the requested business structure.
- Frontend interaction tests: prove clicking `item.reason` toggles a single highlighted sentence and does nothing when evidence metadata is missing.
- Verification: run focused backend pytest targets, focused frontend node tests, then the frontend build.

## Success Criteria

- Each matched compare result can carry a validated evidence sentence index and evidence sentence text.
- Clicking `item.reason` in a chunk card highlights the corresponding source sentence on the left.
- Clicking the same reason again clears the highlight.
- Reasons without usable evidence metadata do not trigger broken or misleading highlighting.
- Exported Excel files use the requested six business columns.
- Matched chunks export one row per matched deviation; unmatched chunks still export one `OTHER` row.
