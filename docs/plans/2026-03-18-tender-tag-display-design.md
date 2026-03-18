# Tender Tag Display Design

## Goal

Fix the homepage compare summary so the tender knowledge-base result area only shows final hit tags, instead of mixing final hit tags with intermediate category candidates.

## Root Cause

`ChunkCard` currently renders two different label sources in the summary area:

- final hit tags from `result.matches[*].type_code`
- classification/category chips from `result.categories`

For tender results, `result.categories` can contain multiple candidate categories even when all actual matches resolve to a single final type code such as `非强制-报价参考`. That causes the summary to show extra labels that do not represent final hits.

## Chosen Approach

- Treat the chunk summary area as a final-result view.
- Render only deduplicated `type_code` tags derived from final `matches`.
- Stop rendering `result.categories` chips in the summary area.
- Keep detailed per-match rows unchanged, because those rows already show the actual type and reason for each hit.

## Files

- `frontend/src/components/ChunkCard.tsx`
- `frontend/tests/chunkCardSummaryTags.test.ts`

## Success Criteria

- A tender result with multiple category candidates but only one final type code shows only one summary tag.
- Standard result summaries keep showing their deduplicated hit tags.
- No extra category chip appears in the summary area.
