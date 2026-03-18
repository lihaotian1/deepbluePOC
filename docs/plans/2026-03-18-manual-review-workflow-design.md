# Manual Review Workflow Design

## Goal

Add a homepage manual-review workflow so users can review each chunk's knowledge-base hits, mark review status, manually adjust match rows, submit the document for review display, and export the updated review state to Excel.

## Confirmed UX Decisions

- The current `预览` / `编辑` source-text buttons stay in the chunk card, but move into the left `原文内容` panel and sit above the `翻译` button.
- The chunk-card header buttons become `修改` and `审核`.
- `审核` toggles to `已审` with a green style, but any later manual change resets that chunk to `审核` / `未审`.
- `修改` opens a second-level modal that lists the current hit rows using the same structure as the expanded result list.
- The second-level modal includes an `添加` action that opens a third-level modal.
- The third-level modal follows the currently active knowledge base, shows that knowledge base's real categories plus `其他`, allows a single entry selection, and requires a non-empty review opinion.
- Choosing `其他` clears the selectable entry list and defaults the opinion to `未命中知识库条目，归类为其他。`.
- The manual opinion continues to use the existing `match.reason` display path, so the current `.chunk-card__reason-text` presentation remains valid.
- Manually added opinions do not bind to source-text highlighting; clicking them should do nothing.
- The compare toolbar adds `提交审核` to the right of `导出 Excel`; confirming submission only changes the display state to `已提交`.
- Excel export must include the latest edited chunk content, the latest manually adjusted match rows, and an additional final `审核状态` column.

## Current-State Findings

### Chunk-card controls and result display

`frontend/src/components/ChunkCard.tsx` already owns the card header actions, source-panel header actions, expanded result list, and reason-highlight behavior. That makes it the natural place for the moved source-view toggles, the new `审核` button, and the nested review-edit modals.

### Homepage orchestration

`frontend/src/pages/HomePage.tsx` already owns document chunks, compare results by knowledge base, chunk editing invalidation, compare streaming, and export triggering. It is the right place to hold document-level submission status and to persist reviewed compare results back to the backend.

### Knowledge-base browsing contract

`frontend/src/api/client.ts` plus `GET /api/v1/knowledge-bases/{file}` already return grouped knowledge-base categories and items. The add-entry modal can reuse that API instead of introducing a new backend lookup route.

### Session-backed export

`backend/app/services/session_store.py` stores chunk content and compare results in memory for the active document session, while `backend/app/services/export_service.py` builds Excel directly from session data. To export manual review changes correctly, reviewed compare results and review metadata must be stored in the same session object.

## Chosen Approach

### 1. Treat reviewed compare results as the canonical export state

After a compare run, each `ChunkCompareResult` should include a `review_status` field initialized to `未审`. When a user edits match rows or reasons, the frontend should overwrite that chunk's result for the active knowledge base and reset `review_status` to `未审`. Clicking `审核` flips only that chunk's `review_status` to `已审`.

### 2. Keep manual row editing inside the existing compare-result model

Manual additions should reuse the existing `MatchItem` shape:

- `entry_id`, `category`, `text`, `type_code` come from the chosen knowledge-base row, or use `OTHER` / `其他` when the user selects `其他`
- `reason` stores the user's review opinion
- `evidence_sentence_index` and `evidence_sentence_text` stay empty for manual entries so the current reason-highlight logic remains non-clickable

This avoids introducing a parallel review-only row model.

### 3. Add a dedicated review-save endpoint for session persistence

Chunk-content edits should keep using `PATCH /documents/{doc_id}/chunks`, because that intentionally invalidates compare results. Manual review edits are different: they update reviewed compare rows and submission state without changing source content. A dedicated endpoint such as `PUT /api/v1/documents/{doc_id}/review` should accept:

- `compare_results_by_kb`
- `submitted_for_review`

The session store should replace its compare-result snapshot with the reviewed version and rebuild compare progress as succeeded records for export and later reads.

### 4. Reset stale review state on any manual change

The frontend should centralize helper functions that:

- toggle a chunk to `已审`
- replace a chunk result's match list
- update an individual row's reason
- remove a row
- append a manual row from a selected knowledge-base item

Every mutating helper should automatically reset that chunk's `review_status` to `未审` so the `审核` button behavior stays consistent.

### 5. Model document submission as lightweight display state

`提交审核` does not need a workflow engine. It only needs:

- a confirmation dialog
- a saved boolean `submitted_for_review`
- UI text `已提交` shown in green after confirmation

The state can live in the document session so it remains stable across export and compare-panel redraws.

### 6. Extend export rows with review status

`backend/app/services/export_service.py` should append `审核状态` as the final column. For matched chunks with multiple rows, the same chunk-level review status repeats on each exported row. For unmatched rows, export `未审` or `已审` according to the result snapshot.

## Alternatives Considered

### A. Keep review state only in the frontend

Rejected because Excel export currently comes from the backend session. A frontend-only review model would require duplicating export logic in the browser or adding a one-off export payload path.

### B. Build a separate review-row model next to compare results

Rejected because the UI and export already understand `ChunkCompareResult` and `MatchItem`. Reusing that shape keeps rendering, filtering, and export changes localized.

### C. Add a dedicated backend endpoint just for fetching categorized review choices

Rejected because `GET /api/v1/knowledge-bases/{file}` already provides the current knowledge base's categories and items in the structure the third-level modal needs.

## File Impact

- `backend/app/schemas.py`
- `backend/app/services/session_store.py`
- `backend/app/api/document_routes.py`
- `backend/app/services/export_service.py`
- `backend/tests/test_document_api.py`
- `backend/tests/test_session_store.py`
- `backend/tests/test_export_service.py`
- `frontend/src/types.ts`
- `frontend/src/api/client.ts`
- `frontend/src/pages/HomePage.tsx`
- `frontend/src/pages/homePageCompareState.ts`
- `frontend/src/components/ChunkCard.tsx`
- `frontend/src/components/ComparePanel.tsx`
- `frontend/src/styles/theme.css`
- `frontend/tests/homePageCompareState.test.ts`
- `docs/plans/2026-03-18-manual-review-workflow-implementation.md`

## Testing Strategy

- Backend first: add failing API/session/export tests for review persistence and the new Excel column.
- Frontend second: add failing pure-state tests for review-status reset, manual row add/remove, and submission-state transitions.
- Verification: run focused backend pytest files, focused frontend `node --test` files, then `npm --prefix frontend run build`.

## Success Criteria

- Chunk cards show moved `预览` / `编辑` controls in the left panel and new `修改` / `审核` controls in the header.
- Clicking `审核` changes the button to green `已审` and stores chunk-level review state.
- Any manual row edit, add, or delete resets the chunk to `未审`.
- `修改` opens a modal that lists current rows and supports editing review opinions, deleting rows, and adding new rows through a categorized selector modal.
- The third-level modal loads categories from the currently active knowledge base and supports the `其他` default opinion flow.
- `提交审核` shows the confirmation copy and, after confirmation, displays green `已提交` text.
- Excel export includes user-edited content, reviewed match rows, and the final `审核状态` column.
