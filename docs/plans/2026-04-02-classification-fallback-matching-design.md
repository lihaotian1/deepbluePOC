# Classification Fallback Matching Design

## Goal

Prevent the two-stage matcher from missing valid knowledge-base entries when the LLM classification step under-selects categories. Chunks that receive no usable item hits after normal classified matching should get a fallback item-matching pass across the remaining categories.

## Confirmed Decisions

- The current pipeline is classification first, item matching second.
- Today, if a category is not returned by classification, that category is never item-matched.
- The fallback should be backend-only and should not require API schema changes.
- Keep the normal classified path unchanged for chunks that already get item hits.
- Use fallback only for chunks that still have zero matched items after the first pass.

## Current-State Findings

### Category misses block item matching completely

`backend/app/services/matcher_service.py` builds `category_chunks` only from classified categories. Any missed category is invisible to `match_items_batch`, which creates false negatives when classification recall is low.

### The existing item matcher is already the best precision filter

The batch item-matching prompt already has stronger evidence requirements and entry-level validation than the category stage. It is a reasonable fallback precision gate after classification fails to produce item hits.

### Backend result schema can already carry recovered hits

`ChunkCompareResult` already supports category lists, matched items, and evidence fields. Fallback recovery can surface as additional matched items without changing response contracts.

## Chosen Approach

### 1. Trigger fallback only for zero-hit chunks

After normal category-based matching finishes for a batch, identify chunks whose `match_rows` are still empty. Only those chunks enter fallback. This keeps cost bounded and avoids disturbing chunks that already matched successfully.

### 2. Run fallback across remaining categories only

For each zero-hit chunk, run `match_items_batch` against every knowledge-base category not already tried in the first pass. If fallback finds hits in a category, append those matches and add the category to the chunk’s category list.

### 3. Keep traces explicit

Add a separate trace event for fallback matching so debugging can distinguish initial classified matching from fallback recovery.

## Alternatives Considered

### A. Retry category classification with a looser prompt

Rejected because it adds another LLM classification step without guaranteeing recall recovery. The item matcher is a more direct fallback validator.

### B. Always match all categories for every chunk

Rejected because it would defeat the purpose of the classification stage and increase cost significantly.

### C. Trigger fallback only when classification returns zero categories

Rejected because a chunk can still be misclassified into the wrong category set and end with zero item hits; fallback should recover those too.

## File Impact

- `backend/app/services/matcher_service.py`
- `backend/tests/test_matcher_logic.py`
- `docs/plans/2026-04-02-classification-fallback-matching-implementation.md`

## Testing Strategy

- Add failing tests first for: no-category fallback recovery, wrong-category fallback recovery, and no extra fallback when an initial hit already exists.
- Implement the minimal matcher-service fallback loop to satisfy those tests.
- Run focused matcher tests, then broader compare-stream backend tests.

## Success Criteria

- Chunks with no initial item hits get a fallback item-matching pass.
- Fallback can recover hits from categories missed by classification.
- Chunks with successful initial hits do not pay fallback cost.
- Response schema remains unchanged.
