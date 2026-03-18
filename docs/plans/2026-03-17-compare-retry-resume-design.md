# Compare Retry And Resume Design

## Goal

Add resilient compare behavior so transient stream/network failures do not discard progress, the frontend automatically retries one interrupted compare request, and manual re-clicking of `比对知识库` only processes failed or still-pending chunks inside the current upload session.

## Confirmed UX Decisions

- Retry state only lives inside the current `doc_id` session.
- A transport-level interruption during streaming should trigger one automatic retry before surfacing a failure.
- Clicking `比对知识库` again should resume work instead of starting from scratch.
- Resume mode must skip chunks that already completed successfully for the selected knowledge base.
- Editing chunk content keeps the current behavior of invalidating compare progress, because saved compare results no longer match the modified source text.

## Current-State Findings

### Frontend streaming behavior

`frontend/src/api/sse.ts` uses `fetchEventSource(...)` and immediately rethrows inside `onerror`, so any network interruption escalates to `TypeError: network error` and aborts the whole compare flow. `frontend/src/pages/HomePage.tsx` catches that error and clears the compare run as a full failure even if earlier chunk results were already rendered.

### Backend compare state model

`backend/app/api/compare_routes.py` processes each selected knowledge base from chunk 1 through chunk N every time the endpoint is called. `backend/app/services/session_store.py` only stores final `compare_results_by_kb`, which means the session remembers successful end results but not per-chunk execution status, failed chunk ids, or resumable work.

### Result rendering dependency

`frontend/src/pages/HomePage.tsx` resets `resultsByKb` at the start of every compare run. That is fine for full reruns, but it would erase successful progress during a resume-only retry workflow.

## Chosen Approach

### 1. Persist per-chunk compare task state in the in-memory session store

Extend the current document session with a compare-progress structure keyed by knowledge-base file name and chunk id. Each chunk record stores:

- `status`: `pending`, `running`, `succeeded`, or `failed`
- `result`: optional `ChunkCompareResult` for succeeded chunks
- `error_message`: optional text for failed chunks

This state stays in memory only, which matches the approved session-only persistence boundary.

### 2. Make the backend compare endpoint resumable by default

When `/api/v1/documents/{doc_id}/compare/stream` receives a request, it should inspect saved chunk state for each selected knowledge base and only schedule chunks whose status is `pending` or `failed`. Chunks already marked `succeeded` are skipped. If no chunk remains for a selected knowledge base, the endpoint still emits a completion summary so the frontend can keep a consistent UI.

### 3. Add one server-side retry for compare batch failures

Within a compare run, each failing batch should be retried once before chunks are marked failed. This handles transient LLM/API/network errors close to the backend and avoids wasting a whole front-end retry when only one batch needs a second attempt.

### 4. Add one frontend retry for interrupted SSE transport

`streamCompare(...)` should perform one automatic reconnect attempt when the SSE request itself fails to open or is interrupted by a transport-level error. This retry is request-level, not chunk-level. Because the backend now resumes from session state, the restarted request naturally skips already-succeeded chunks and continues unfinished work.

### 5. Preserve completed results on resume instead of clearing them

`HomePage.tsx` should stop wiping `resultsByKb` at the beginning of every compare attempt. Instead, it keeps the existing successful results in place, merges in new chunk results, and updates progress/log text to explain whether the current run is a first pass, an automatic retry, or a manual resume.

### 6. Keep edit invalidation strict

The existing `patchChunks(...)` and local chunk edit flow should still clear compare state for the document. Once chunk content changes, both saved results and retry statuses become stale, so the system should restart compare progress from `pending` for all selected knowledge bases.

## Alternatives Considered

### A. Frontend-only retry with no backend resume state

Rejected because it cannot satisfy manual resume semantics. A second click would still resubmit every chunk and re-run already completed LLM work.

### B. Persist retry state across refreshes or deployments

Rejected because the approved scope is current-session only and the existing app architecture uses in-memory session state. Adding persistence would require a different storage layer and larger operational changes.

### C. Mark whole batches as succeeded/failed without chunk-level detail

Rejected because users want to skip already completed entries. Batch-only bookkeeping would either over-retry successful chunks or require more brittle frontend-side inference.

## Component / File Impact

- `backend/app/schemas.py`
  - add compare progress models or typed fields for per-chunk status records
- `backend/app/services/session_store.py`
  - initialize compare progress for new sessions
  - save succeeded/failed chunk state by knowledge base
  - expose helpers for resumable chunk selection and compare reset on chunk edits
- `backend/app/api/compare_routes.py`
  - select only pending/failed chunks
  - retry failed batches once
  - emit richer completion/error summary events
- `backend/tests/test_session_store.py`
  - verify per-chunk status lifecycle and reset rules
- `backend/tests/test_compare_stream_api.py`
  - verify auto-resume skips succeeded chunks and only retries pending/failed work
- `frontend/src/api/sse.ts`
  - add one automatic transport retry and explicit retry-status callbacks
- `frontend/src/pages/HomePage.tsx`
  - preserve successful results across retries
  - present resume-aware logs and progress text
- `frontend/src/pages/homePageCompareState.ts`
  - add small helpers if needed for merge/reset semantics
- `frontend/src/types.ts`
  - add any new event/status payload types used by the UI
- `frontend/tests/*.test.ts`
  - add focused coverage for auto-retry and resume-only behavior

## Testing Strategy

- Backend tests first: prove session state tracks chunk statuses, compare-stream retries one failing batch, and reruns skip already succeeded chunk ids.
- Frontend tests second: prove the SSE wrapper retries once on network failure and that compare state merging preserves completed results during resume.
- Verification: run targeted backend pytest commands, targeted frontend `node --test` commands, then the frontend build.

## Success Criteria

- A transient SSE transport failure triggers exactly one automatic retry.
- Manual re-clicking `比对知识库` only processes `pending` or `failed` chunks for each selected knowledge base.
- Successfully completed chunk results remain visible and are not recalculated during resume.
- Failed chunks remain retryable inside the current upload session.
- Editing chunk content clears stale compare progress and forces a fresh run.
- Existing upload, compare, and export flows still pass regression tests.
