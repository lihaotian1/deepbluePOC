# Sidebar Homepage KB Polish Design

## Goal

Apply the next round of UI polish to the React frontend: keep the sidebar fixed and always expanded, move the `智能比对` brand title into the homepage hero, enlarge the logo, and fix knowledge-base editor textareas so long content is fully visible while editing.

## Constraints

- Keep the existing `AppShell` + sidebar + page composition intact.
- Preserve the existing navigation items and knowledge-base submenu behavior.
- Do not reintroduce collapse/expand behavior anywhere in the sidebar.
- Keep the current visual language rather than redesigning the app.
- Fix textarea visibility for both grouped and flat knowledge-base editors.

## Chosen Approach

### 1. Sidebar stays fixed by layout, not by a floating overlay

The current layout already has a two-column `app-shell`. The simplest and safest change is to make the shell fill the viewport, let `.app-main` own vertical scrolling, and keep the sidebar pinned within the shell. This avoids the extra offset bookkeeping that a fully `position: fixed` sidebar would require.

### 2. Remove collapse state entirely

The current sidebar still carries `collapsed` props, alternate markup, and a toggle button. Those branches will be removed from `App.tsx`, `AppShell.tsx`, `Sidebar.tsx`, and the corresponding CSS so the menu always renders in its expanded state.

### 3. Make the logo the visual anchor of the sidebar

`app-sidebar__top` will keep a single full-width logo button. The image itself will stretch to the container width with `width: 100%` and `height: auto`, preserving aspect ratio and making the logo visually fill the sidebar header.

### 4. Move the brand title into the homepage hero

The sidebar title `智能比对` will be removed. The homepage hero will keep `AI Assistant` as the eyebrow and add `智能比对` as the main `h1`, making the brand visible where the user starts work.

### 5. Fix KB editor height with shared textarea autosizing

The knowledge-base editor currently uses a fixed-height textarea style, so long entries get clipped. A shared textarea autosize helper will measure `scrollHeight` and set the element height on mount and on each value change. The same helper can also replace the duplicated logic already present in `ChunkCard`.

## Alternatives Considered

### A. Fully fixed sidebar with manual content offset

Rejected because it introduces more responsive edge cases and requires manually managing main-content spacing.

### B. CSS-only textarea sizing

Rejected because textarea height does not truly adapt to content with CSS alone in this codebase; long entries still need JS-driven height measurement.

### C. Separate autosize logic in each component

Rejected because the project already has one autosizing behavior in `ChunkCard`; duplicating that logic again in the knowledge-base page would make future textarea fixes drift.

## Data Flow / Component Impact

- `App.tsx`: remove sidebar collapsed state and toggle handler.
- `AppShell.tsx`: simplify props passed to the sidebar.
- `Sidebar.tsx`: remove toggle UI and collapsed branches; keep logo + nav only.
- `HomePage.tsx`: render `智能比对` as the main hero heading under `AI Assistant`.
- `KnowledgeBasePage.tsx`: replace plain KB textareas with autosizing textareas for grouped and flat content.
- `ChunkCard.tsx`: reuse the same autosize helper so content editing behavior stays consistent.
- `theme.css`: update sidebar sizing/fixed behavior, remove collapse styles, enlarge logo styling, and remove fixed KB textarea height assumptions.

## Testing Strategy

- Add a frontend unit test for the textarea autosize helper.
- Use that test as the red/green cycle for the editor-height bug.
- Run the existing frontend pagination test to guard against regressions in the KB page.
- Run `npm --prefix frontend run build` to verify the updated component tree and styles compile.

## Success Criteria

- Sidebar does not scroll away while the right content area scrolls.
- Sidebar always appears expanded and has no collapse button.
- Logo fills the sidebar header width proportionally.
- Sidebar title `智能比对` is gone.
- Homepage hero shows `AI Assistant` and `智能比对` in that order.
- Knowledge-base editor textareas expand to show full content instead of clipping long text.
