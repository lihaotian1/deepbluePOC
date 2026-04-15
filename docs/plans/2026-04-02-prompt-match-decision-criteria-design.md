# Prompt Match Decision Criteria Design

## Goal

Strengthen the LLM prompt instructions so matching is no longer driven only by semantic similarity. The prompts must explicitly distinguish strong association, conditional support, strong association with conflict, and theme-only similarity, while preserving the current response schema.

## Confirmed Decisions

- Semantic similarity alone is not enough for a category or entry to match.
- Matching should prioritize same object, same requirement dimension, and same constraint context.
- Strongly associated but conflicting items should be kept as weak hits instead of being dropped.
- Theme-only similarity without the same object or constraint should not match.
- The API response shape stays unchanged; conflict/strength guidance is expressed through prompt rules and `reason` text.

## Current-State Findings

### Prompts currently optimize only for semantic support

`backend/app/services/prompt_builder.py` currently tells the model to judge whether DeepBlue content can cover, satisfy, or support a requirement, but it does not explicitly describe how to rank strong associations, how to handle conflicting entries, or how to reject topic-only similarities.

### Existing output schema is sufficient

`backend/app/services/llm_client.py` and `backend/app/schemas.py` only require category lists plus match rows containing `entry_id`, `reason`, and evidence fields. The current shape can still carry stronger decision criteria by standardizing what `reason` should explain.

### Prompt-only behavior changes are low-risk

The business requirement is about model judgment policy rather than transport format. Updating prompt instructions and locking the wording with tests avoids a wider backend/frontend contract change.

## Chosen Approach

### 1. Add explicit ranking criteria to classification prompts

Classification prompts should tell the model to first check whether the inquiry requirement and the category sample entries refer to the same object, same ability or deliverable, and same limiting condition. A category is worth returning when it contains material that is either directly supportive, conditionally supportive, or strongly associated but conflicting.

### 2. Add explicit relation classes to item-matching prompts

Item prompts should define four judgment buckets:

- strong association and direct support
- strong association and conditional support
- strong association but conflict
- topic-only similarity with insufficient alignment

The model should return the first three and reject the fourth.

### 3. Standardize `reason` wording expectations

Prompts should instruct the model to explain whether the hit is direct support, conditional support, or strong association with conflict. This preserves the current JSON schema while making downstream review easier.

## Alternatives Considered

### A. Add new JSON fields like `match_strength` and `conflict`

Rejected for now because it would require broader parsing and contract changes for limited immediate value.

### B. Drop all conflicting items

Rejected because the confirmed requirement is to keep strongly associated conflicts as weak hits.

### C. Keep prompts as generic semantic matching

Rejected because it is the root cause of unrelated-but-similar entries being over-selected.

## File Impact

- `backend/app/services/prompt_builder.py`
- `backend/tests/test_matcher_logic.py`
- `docs/plans/2026-04-02-prompt-match-decision-criteria-implementation.md`

## Testing Strategy

- Add failing tests first for prompt text covering strong association, conflict retention, and topic-only exclusion.
- Implement the minimal prompt wording changes to make the tests pass.
- Run focused matcher prompt tests, then the broader matcher and compare-stream backend tests.

## Success Criteria

- Classification prompts say semantic similarity alone is insufficient.
- Item prompts explicitly distinguish direct support, conditional support, strong association with conflict, and topic-only similarity.
- Conflicting but strongly associated items remain allowed in output.
- Theme-only similar items are explicitly excluded.
- Existing JSON schemas and evidence constraints remain unchanged.
