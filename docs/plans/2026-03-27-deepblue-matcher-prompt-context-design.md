# DeepBlue Matcher Prompt Context Design

## Goal

Update the knowledge-base smart-analysis prompts so the LLM understands the business meaning of each input: the source text is a quotation inquiry requirement for DeepBlue, and the knowledge-base categories and entries represent content DeepBlue can provide in response. The classification stage should use category sample entries to decide whether a requirement can be covered by a category, and the item-matching stage should use the same business framing to choose supporting entries.

## Confirmed Decisions

- The source `chunk` / `chunks` content is always inquiry-document text describing requirements for DeepBlue.
- Knowledge-base categories and entries describe capabilities,方案, or response content that DeepBlue can provide.
- Classification should record a category when DeepBlue can satisfy, cover, or respond to the requirement through that category.
- Classification should include category sample entries so the model has concrete capability context instead of bare category names.
- Item matching should remain multi-select and must continue rejecting hallucinated `chunk_id` and `entry_id` values.

## Current-State Findings

### Classification prompts only expose category names today

`backend/app/services/prompt_builder.py` currently sends `category_keys` without any representative entry text, so the model has category labels but little evidence about what DeepBlue can actually provide within each category.

### Matcher orchestration already has the data needed for samples

`backend/app/services/matcher_service.py` has access to the loaded `KnowledgeBase`, so it can build lightweight per-category sample payloads without changing storage format or loader behavior.

### Item matching already carries strong structural safeguards

The batch item prompt already requires `evidence_sentence_index` and `evidence_sentence_text`, and `backend/app/services/llm_client.py` filters unknown IDs. The prompt update should preserve these output contracts while clarifying the business semantics.

## Chosen Approach

### 1. Enrich classification payloads with category contexts

Keep `category_keys` for response validation, but add `category_contexts` to the prompt payload. Each context includes the category name and a small set of representative sample entries drawn from the knowledge base. This gives the LLM explicit evidence of what DeepBlue can provide under that category.

### 2. Rewrite both prompt stages around the same business framing

Update classification and item-matching system prompts so they explicitly define:

- `chunk` / `chunks`: inquiry requirements aimed at DeepBlue
- categories: DeepBlue capability groupings
- candidates: specific content DeepBlue can provide

The matching logic should instruct the model to decide whether a DeepBlue category or entry can satisfy or support the requirement, not merely whether words overlap.

### 3. Preserve strict structured-output constraints

Keep the existing JSON-only response formats, multi-select behavior, duplicate filtering, and evidence-sentence constraints. The change is semantic guidance plus richer input context, not a response-schema redesign.

## Alternatives Considered

### A. Prompt-only wording refresh without category samples

Rejected because the user explicitly wants stronger background guidance, and bare category names still leave too much ambiguity during classification.

### B. Send every category entry during classification

Rejected because it would increase token usage significantly and is unnecessary when a compact sample set can provide enough context.

### C. Add separate per-knowledge-base custom prompts

Rejected for now because the requested business framing applies to both knowledge bases, and the current shared prompt-builder design remains simpler to maintain.

## File Impact

- `backend/app/services/prompt_builder.py`
- `backend/app/services/llm_client.py`
- `backend/app/services/matcher_service.py`
- `backend/tests/test_matcher_logic.py`
- `docs/plans/2026-03-27-deepblue-matcher-prompt-context-implementation.md`

## Testing Strategy

- Add failing tests first for classification prompt content, category sample payloads, and strengthened item-matching wording.
- Implement the minimum prompt-builder and matcher-service changes needed to satisfy those tests.
- Run focused matcher/prompt tests, then run the broader compare-stream backend tests impacted by the LLM interface.

## Success Criteria

- Classification prompts explicitly state that the source text is a requirement for DeepBlue and the category contexts represent what DeepBlue can provide.
- Classification payloads include representative sample entries per category.
- Item-matching prompts explicitly state that candidates are DeepBlue-provided content used to satisfy the requirement.
- Existing JSON response contracts and hallucination guards stay intact.
- Backend matcher and compare tests pass with the new prompt structure.
