# Homepage Pagination Design

## Goal

Add homepage pagination around the filtered chunk list so users can switch pages from both the top and bottom of the list, reuse the knowledge-base pagination presentation, and see how many items on the current page have already been reviewed.

## Confirmed UX Decisions

- The homepage reuses the same pagination structure and styling as the knowledge-base page by rendering `.kb-pagination-bar` and `.kb-pagination-bar__actions`.
- The pagination bar appears immediately below the homepage type-filter panel and again below the chunk list.
- Each page always targets 10 chunk cards.
- The `已审` counter sits to the left of the `上一页` button and uses the format `已审：x/y`.
- The denominator `y` uses the current page's actual item count, so a short final page can show values like `已审：2/3`.
- The homepage does not add the knowledge-base page's `新增章节` / `新增分类` action.

## Current-State Findings

### Homepage chunk orchestration

`frontend/src/pages/HomePage.tsx` already owns the sorted chunk list, active knowledge-base result map, result filtering, and review-state updates. That makes it the correct place to keep the current page state and render the duplicated pagination bars.

### Knowledge-base pagination contract

`frontend/src/pages/KnowledgeBasePage.tsx` and `frontend/src/pages/knowledgeBasePagination.ts` already establish the desired visual structure and page-model pattern: compute pagination metadata in a pure helper, then render `.kb-pagination-bar` with page summary text and action buttons.

### Review-state source of truth

The current review status is stored inside each `ChunkCompareResult` in `resultsByKb`, and `normalizeReviewResult` in `frontend/src/pages/homePageReviewState.ts` ensures missing values are treated as `未审`. The per-page reviewed counter should therefore derive from the current page's `chunk_id` values plus the active knowledge-base result map.

## Chosen Approach

### 1. Add a dedicated homepage pagination helper

Create a small pure helper module that accepts the already filtered chunk list, the active result map, the requested page, and the fixed page size. It should return:

- the corrected current page number
- the current page's chunk slice
- total item count
- total page count
- current page item count
- current page reviewed count

This keeps pagination math, page clamping, and review counting testable outside React.

### 2. Keep pagination downstream of existing filters

The homepage should continue to sort chunks first and apply the active type filter second. Pagination should run after that filtering so both the top and bottom pagers always reflect exactly the cards currently visible for the selected knowledge-base view.

### 3. Reset page state on user flows that change the visible result set

The page should reset to `1` when:

- a new document is uploaded
- a new compare run starts
- the active type filter changes
- the active result knowledge base changes

If the result set shrinks for any other reason, the pagination helper should clamp the requested page to the last available page instead of leaving the UI on an empty page.

### 4. Render one shared pager shape twice

`HomePage.tsx` should render the same pager markup above and below the chunk list, both wired to the same `page` state. The top pager sits under the filter panel, and the bottom pager sits after the chunk cards. Both should disable `上一页` and `下一页` at the same boundaries.

## Alternatives Considered

### A. Keep pagination logic inline inside `HomePage.tsx`

Rejected because the page already handles compare streaming, export sync, chunk editing, and review changes. Pulling pagination math into a pure helper keeps the component readable and makes the reviewed-count behavior easy to verify.

### B. Reuse `knowledgeBasePagination.ts` directly

Rejected because the knowledge-base page paginates knowledge-base categories and items, while the homepage needs chunk slices plus review-count metadata. The rendering structure is reusable, but the data model is different enough to justify a dedicated helper.

### C. Extract a shared pagination React component now

Rejected for this change because the request only targets homepage behavior. Reusing the existing class names gives visual consistency without widening the refactor scope.

## File Impact

- `frontend/src/pages/HomePage.tsx`
- `frontend/src/pages/homePagePagination.ts`
- `frontend/tests/homePagePagination.test.ts`
- `docs/plans/2026-03-19-homepage-pagination-implementation.md`

## Testing Strategy

- Add failing pure tests for homepage pagination slicing, page clamping, and per-page reviewed counting.
- Implement the minimal helper to make those tests pass.
- Wire the helper into `HomePage.tsx` and run the focused pagination test file plus the homepage review-state tests as a regression check.
- Run `npm --prefix frontend run build` to verify the updated page compiles.

## Success Criteria

- The homepage shows a pagination bar below the type-filter panel and another at the bottom of the chunk list.
- Both bars match the knowledge-base pagination layout and keep page state synchronized.
- Each page shows at most 10 chunk cards.
- The current page summary shows the total filtered item count and current page number.
- The `已审：x/y` text reflects only the current page's items and updates when review status changes.
- A short last page uses its actual item count as the denominator.
