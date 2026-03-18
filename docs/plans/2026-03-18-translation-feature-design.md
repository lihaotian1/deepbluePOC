# LLM Translation Toggle Design

## Goal

Add a per-chunk translation toggle on the homepage so users can translate the current source paragraph into Chinese with the existing LLM backend, switch back to the original text, and see translation progress through the existing `pulse-dot` status affordance.

## Confirmed UX Decisions

- The feature lives on each homepage chunk card in the `原文内容` panel.
- The new control should visually match the existing `展开` / `收起` button on the result panel.
- Translation is one-way only: source text to Chinese.
- The translated text is a view-only overlay and must not overwrite `chunk.content`.
- After translation finishes, the button changes from `翻译` to `原文`.
- During translation, the button becomes disabled and shows an animated `pulse-dot` on its left.
- After translation succeeds, the dot stays visible but becomes static until the user switches back to the original text.
- Editing the source text invalidates any cached translation for that chunk.

## Current-State Findings

### Frontend card layout

`frontend/src/components/ChunkCard.tsx` renders the `原文内容` header on the left and already uses a small `mini-toggle` button on the right-side result panel for `展开` / `收起`. That makes `ChunkCard` the correct place to host a new translation toggle with matching layout and per-card state.

### Existing status affordance

`frontend/src/styles/theme.css` already defines `.pulse-dot` as the animated compare-status indicator. The translation feature can reuse that class and add a static modifier instead of inventing a second status pattern.

### Backend model access

`backend/app/main.py` already wires a shared `OpenAICompatibleMatcherLLM` instance into `app.state.matcher_llm`. `backend/app/services/llm_client.py` already wraps OpenAI-compatible chat completion requests and JSON parsing, so translation should extend that client rather than introducing a separate vendor-specific service.

### API shape consistency

`frontend/src/api/client.ts` centralizes HTTP requests through a shared Axios client. Adding a dedicated translation function there keeps the homepage UI aligned with the existing API access pattern.

## Chosen Approach

### 1. Add a dedicated backend translation endpoint

Create a focused API endpoint that accepts plain text and returns Chinese translation only. The endpoint should not mutate any document session state, because translation in this feature is a read-only helper for the UI.

Suggested contract:

- `POST /api/v1/translate/chinese`
- request: `{ "text": string }`
- response: `{ "translation": string }`

This keeps the scope tight and avoids mixing translation behavior into upload or compare routes.

### 2. Reuse the existing LLM client with a translation method

Extend `OpenAICompatibleMatcherLLM` with `translate_to_chinese(...)`, built on top of `_chat_json(...)`. The prompt should instruct the model to:

- translate the input into simplified Chinese
- preserve technical meaning and units
- avoid commentary or explanations
- return JSON with a single `translation` field

This preserves the existing transport, auth, timeout, and response parsing behavior.

### 3. Keep translation state local to each chunk card

`ChunkCard.tsx` should own a small view-state model for translation because the behavior is purely presentational and scoped to a single card. The state needs to track:

- whether translation is in progress
- whether translated text is currently displayed
- the cached translated text
- the original-source snapshot used to produce that translation
- any lightweight translation error message

This avoids polluting homepage-level compare state with UI-only translation concerns.

### 4. Cache successful translations but invalidate them on source edits

When the user clicks `翻译` for the first time, the card should request a translation and cache the result. If the user then clicks `原文`, the card switches back to the original text without discarding the cached Chinese result. A second click on `翻译` should reuse that cache.

If `chunk.content` changes, the cached translation becomes stale and should be cleared immediately. The card should revert to the original-text view, hide the dot, and restore the `翻译` button label.

### 5. Reuse `pulse-dot` with a static variant

The translation toggle should show:

- no dot before any translation request
- animated `.pulse-dot` while the request is running
- visible static dot after a successful translation while the translated view is active

The static state can be implemented with a modifier class that removes the animation and leaves the same color token.

### 6. Fail safely without altering source content

If the request fails or returns invalid data:

- keep showing the original text
- re-enable the button
- hide the status dot
- show a small inline error message such as `翻译失败，请重试`

The feature should never write translated content into `chunk.content`, trigger chunk invalidation logic, or affect compare/export flows.

## Alternatives Considered

### A. Translate directly from the frontend with the model provider

Rejected because the app already centralizes model access in the backend. Frontend-side translation would expose credentials/configuration and diverge from the current architecture.

### B. Replace `chunk.content` with the translated text

Rejected because the approved UX is a view-only translation toggle. Writing translated text into the editable source field would blur the boundary between translation, document editing, compare invalidation, and export behavior.

### C. Store translation state on `HomePage.tsx`

Rejected because translation is independent per chunk card and does not need cross-card coordination. Local card state is simpler and better isolated.

## Component / File Impact

- `backend/app/services/llm_client.py`
  - add prompting and JSON extraction for Chinese translation
- `backend/app/schemas.py` or a new route-local request/response model location
  - define translation request/response payloads
- `backend/app/api/translation_routes.py`
  - add the focused translation endpoint
- `backend/app/main.py`
  - register the translation router
- `backend/tests/`
  - add focused API and/or client tests for translation success and failure cases
- `frontend/src/api/client.ts`
  - add a `translateChunkContent(...)` helper
- `frontend/src/components/ChunkCard.tsx`
  - add translation button, state handling, request flow, stale-result protection, and view switching
- `frontend/src/styles/theme.css`
  - add layout and static-dot styles for the translation control
- `frontend/tests/`
  - add focused tests for translation state transitions and invalidation on source edit

## Testing Strategy

- Backend first: add a failing test for the new translation endpoint and LLM client behavior.
- Frontend second: add failing state-transition tests for the per-card translation model, especially request lifecycle, cache reuse, and source-edit invalidation.
- Verification: run focused backend pytest tests, focused frontend `node --test` suites, then `npm --prefix frontend run build`.

## Success Criteria

- Each homepage chunk card shows a `翻译` button in the source-panel header with styling aligned to `展开` / `收起`.
- Clicking `翻译` disables the button and shows an animated `pulse-dot` on its left.
- On success, the card displays Chinese text, changes the button label to `原文`, keeps a visible static dot, and re-enables the button.
- Clicking `原文` switches back to the original text without losing the cached translation.
- Editing the source text clears the cached translation and stale status.
- Translation failures do not alter the source content or break existing compare/export behavior.
