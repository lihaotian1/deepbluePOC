# Smart Analysis Copy Refresh Design

## Goal

Refresh the homepage analysis workflow wording so user-visible copy uses `智能分析` instead of `比对`, and add a compact progress bar to the analysis-panel status row next to the existing `pulse-dot`.

## Confirmed UX Decisions

- Only user-visible frontend copy changes; internal interface names, component names, and API names stay unchanged.
- The analysis panel title changes from `知识库比对` to `知识库智能分析`.
- Buttons, helper text, empty states, logs, and progress messages that currently say `比对` change to `智能分析` or equivalent user-facing wording.
- The new progress bar appears only in the analysis panel status row beside the `pulse-dot`.
- The translation status indicator inside chunk cards keeps its current dot-only presentation.

## Current-State Findings

### Visible analysis wording is concentrated in a few frontend files

`frontend/src/components/ComparePanel.tsx`, `frontend/src/components/comparePanelViewState.ts`, `frontend/src/pages/HomePage.tsx`, and `frontend/src/components/ChunkCard.tsx` contain the runtime copy that users actually see today. These files cover the panel heading, CTA button, status text, log messages, and result labels.

### The status row already has a stable structure

`ComparePanel.tsx` renders a compact status row with `.compare-panel__status`, a `.pulse-dot`, and `progressText`. This is the right insertion point for a small progress bar because it is already the single visual status summary for the current streaming run.

### Progress data already exists, but only as text

`HomePage.tsx` receives `chunk_start` events that include `index` and `total`, and it already uses those values to build user-visible text like `x/y`. The progress bar can reuse those numbers instead of introducing a second async data source.

## Chosen Approach

### 1. Rename only runtime UI copy

Update visible app strings from `比对` to `智能分析` where they affect the actual frontend experience:

- panel headings and helper text
- action button labels
- result/empty-state hints
- progress text and failure text
- streaming log lines

Docs, plan files, internal identifiers, and API contracts stay unchanged.

### 2. Add explicit analysis-progress state in `HomePage.tsx`

Keep the existing `progressText` for human-readable messaging and add a small numeric progress state derived from streaming events. A minimal model is enough:

- `current`: current processed chunk index for the active knowledge base
- `total`: chunk total for that active run

The page should reset this state on upload, before a new analysis run, on completion, and on failure.

### 3. Make `ComparePanel` a pure presenter for the bar

Pass the progress numbers into `ComparePanel.tsx` and let the panel derive a width percentage or fill state for a narrow status bar. This keeps calculation near the streaming logic while leaving rendering and CSS localized to the panel.

### 4. Keep the progress bar visually lightweight

The new bar should support three simple states:

- idle/unknown progress: empty low-emphasis track
- active analysis: partially filled track based on `current / total`
- completed analysis: full track

No extra labels or second status legend are needed because `progressText` already explains the current phase.

## Alternatives Considered

### A. Global text search-and-replace for all `比对` occurrences

Rejected because many matches live in docs and internal plans rather than runtime UI. The confirmed scope is only user-visible copy in the application.

### B. Reuse only `progressText` and parse `x/y` back into a progress bar

Rejected because string parsing would be brittle and tightly coupled to Chinese copy. The event payload already provides structured numbers, so the progress bar should use structured state directly.

### C. Add the progress bar to every `pulse-dot`

Rejected because the translation indicator in `ChunkCard.tsx` represents a separate feature and the user explicitly scoped the new bar to the analysis panel only.

## File Impact

- `frontend/src/pages/HomePage.tsx`
- `frontend/src/components/ComparePanel.tsx`
- `frontend/src/components/comparePanelViewState.ts`
- `frontend/src/components/ChunkCard.tsx`
- `frontend/src/styles/theme.css`
- `frontend/tests/comparePanelViewState.test.ts`
- `docs/plans/2026-03-19-smart-analysis-copy-implementation.md`

## Testing Strategy

- Add failing tests for the compare-panel view-state copy and progress calculations first.
- Implement the minimal view-state helper changes to make those tests pass.
- Wire the new progress props into `HomePage.tsx` and `ComparePanel.tsx`.
- Run the focused compare-panel and homepage review tests, then run `npm --prefix frontend run build`.

## Success Criteria

- Users see `智能分析` instead of `比对` across the runtime analysis workflow.
- The analysis panel heading reads `知识库智能分析`.
- The main analysis button and status copy use the updated wording.
- Logs and progress messages shown during streaming use the updated wording.
- The analysis panel status row shows a small progress bar to the right of the `pulse-dot`.
- The progress bar advances during streaming and fills when analysis completes.
- The chunk-card translation status dot remains unchanged.
