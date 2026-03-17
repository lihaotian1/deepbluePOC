# Homepage Card And Splitter Iteration Design

## Goal

Refine homepage compare cards so collapsed and expanded states behave exactly as requested, remove artificial numbering from homepage chunk titles, and improve upload-time chapter splitting so GPT is used first with a safe rule-based fallback.

## Confirmed UX Decisions

- Homepage compare cards default to the collapsed state.
- In the collapsed state, the right panel shows only tags, not detailed match text or reasons.
- The collapsed card height is driven by the right panel tag area, with a minimum of three tag rows.
- The left source panel always mirrors the right panel height.
- In the collapsed state, any source text beyond that synchronized height is truncated with an ellipsis.
- In the expanded state, both sides fully expand and the final card height is the greater of the left source content height and the right detailed-result height, so neither side is clipped.
- Homepage chunk titles should display the parsed heading only, without the extra frontend-added chunk index prefix.
- Upload-time document splitting should use GPT first and fall back to the current engineering rules when GPT is unavailable or unreliable.

## Current-State Findings

### Homepage cards

`frontend/src/components/ChunkCard.tsx` currently prepends `chunk.chunk_id` to the visible title, always renders detailed compare content in the right panel, and only uses a simple clamp for expansion. It does not have a synchronized two-panel height model, and the left source panel is not driven by the right panel state.

### Splitter pipeline

`backend/app/services/splitter_service.py` currently calls only `split_text_engineering(...)` during uploads, so prompt changes alone do not affect the web upload flow. In `chapter_splitter.py`, the GPT path only selects leaf headings from already-detected heading candidates, which means missing candidates such as a skipped `1.8` cannot be recovered only by better GPT instructions.

## Chosen Approach

### 1. Homepage card layout becomes result-driven in collapsed mode

The right panel will expose two explicit rendering states:

- `collapsed`: render only compact tags and status
- `expanded`: render tags plus detailed matched entries and reasons

The card height will be computed from measured content, not a fixed clamp. In collapsed mode, the right panel determines the baseline height with a minimum equal to three tag rows. The left panel will adopt that same height and use visual truncation with ellipsis. In expanded mode, the card height becomes `max(leftFullHeight, rightDetailHeight)`, which matches the user’s correction that expanded height should follow whichever side is taller.

### 2. Title cleanup stays frontend-only

The backend chunk data will remain unchanged. `ChunkCard` will stop prefixing `chunk.chunk_id` in the displayed title and will render `chunk.heading` directly.

### 3. GPT-first upload splitting with engineering fallback

The upload path will move from engineering-only splitting to:

1. detect text
2. try GPT-assisted leaf selection
3. if GPT fails, returns invalid data, or no usable output, fall back to rule-based engineering split

This keeps uploads robust while making prompt improvements actually affect the app.

### 4. Better heading candidate detection plus stricter GPT instructions

To address skipped mid-sequence headings like `1.8`, the solution cannot rely on prompt wording alone. The heading detector and GPT prompt will both be strengthened:

- make numeric heading detection more tolerant of real RFQ formatting variations
- explicitly instruct GPT not to skip intermediate numbering when the heading exists in the candidate set
- keep rule-based minimum-leaf filtering as a guardrail after GPT returns indices

### 5. GPT splitter should use project LLM config, not a hardcoded endpoint

The GPT splitter currently hardcodes the OpenAI chat completions endpoint. The upload service should use the app’s configured base URL, model, key, and timeout so the splitter behaves consistently with the rest of the app.

## Alternatives Considered

### A. CSS-only clamp on the left, fixed clamp on the right

Rejected because it cannot satisfy the corrected expanded-state rule where the final height must be the larger of the two fully rendered sides.

### B. Always render full right details and only visually hide them

Rejected because the collapsed card should semantically be tag-only, not a visually clipped version of details; it also complicates synchronized height measurement.

### C. Prompt-only splitter changes

Rejected because the current upload path does not use GPT, and even in the GPT helper, a missing heading candidate cannot be restored by prompt changes alone.

## Component / File Impact

- `frontend/src/components/ChunkCard.tsx`
  - remove visible numeric prefix from titles
  - split result panel into collapsed tag view and expanded detail view
  - synchronize left/right height by measured state
- `frontend/src/styles/theme.css`
  - add collapsed tag-area sizing and left-panel truncation styles
  - remove old clamp assumptions that conflict with the new synchronized behavior
- `frontend/src/types.ts` or helper files only if a small view-model helper improves testability
- `backend/app/services/splitter_service.py`
  - switch upload splitting to GPT-first with fallback
- `backend/app/config.py`
  - add any missing splitter-related config if needed
- `chapter_splitter.py`
  - improve heading detection
  - accept configurable GPT endpoint usage
  - strengthen GPT messages and validation

## Testing Strategy

- Frontend: add focused tests for card state/view-model logic such as collapsed tags-only state, expanded max-height rule, and title formatting without the prefixed chunk number.
- Backend: add tests proving upload splitting can use GPT-first fallback behavior and that heading detection/GPT selection does not skip a valid intermediate heading candidate.
- Verification: run targeted frontend node tests, backend pytest coverage for splitter/document upload, then the full frontend build and backend test suite.

## Success Criteria

- Collapsed homepage cards show only tags on the right.
- Collapsed card height is driven by right-side tag content with a minimum of three tag rows.
- Collapsed left source panel matches that height and truncates overflow with ellipsis.
- Expanded cards show full right details and full left source content.
- Expanded card height equals the larger of the left full content height and right detailed result height.
- Homepage titles no longer show the extra frontend numeric prefix.
- Upload splitting uses GPT first, safely falls back to engineering rules, and is more robust against missed intermediate section headings.
