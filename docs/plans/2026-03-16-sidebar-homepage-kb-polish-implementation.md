# Sidebar Homepage KB Polish Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the sidebar fixed and always expanded, move the `智能比对` brand title into the homepage hero, enlarge the logo, and fix knowledge-base editor textarea autosizing.

**Architecture:** Keep the existing `AppShell` layout and remove sidebar collapse logic instead of replacing the shell structure. Introduce one shared textarea autosize helper for both chunk editing and knowledge-base editing so long content is visible without duplicating height logic.

**Tech Stack:** React 18, TypeScript, Vite, existing Node `node:test` tests, existing CSS theme.

---

### Task 1: Textarea autosize helper

**Files:**
- Create: `frontend/src/utils/textareaAutosize.ts`
- Create: `frontend/tests/textareaAutosize.test.ts`

**Step 1: Write the failing test**

Add tests that verify:
- the helper respects a minimum height
- the helper grows when `scrollHeight` is larger than the minimum
- the helper resets to `auto` before applying the measured height

**Step 2: Run test to verify it fails**

Run: `node --test --experimental-strip-types frontend/tests/textareaAutosize.test.ts`
Expected: FAIL because the helper file does not exist yet.

**Step 3: Write minimal implementation**

Implement a small helper that accepts a textarea-like element, clears `style.height`, and then applies `Math.max(scrollHeight, minHeight)` in pixels.

**Step 4: Run test to verify it passes**

Run: `node --test --experimental-strip-types frontend/tests/textareaAutosize.test.ts`
Expected: PASS.

### Task 2: Use shared autosize in editors

**Files:**
- Modify: `frontend/src/components/ChunkCard.tsx`
- Modify: `frontend/src/pages/KnowledgeBasePage.tsx`
- Modify: `frontend/src/styles/theme.css`

**Step 1:** Use Task 1 test as the red foundation.

**Step 2:** Replace the inline autosize logic in `ChunkCard.tsx` with the shared helper.

**Step 3:** Add autosizing behavior to the grouped and flat knowledge-base textareas in `KnowledgeBasePage.tsx`.

**Step 4:** Remove fixed KB textarea height assumptions from `theme.css` while keeping non-resizable behavior.

**Step 5:** Run frontend tests and build.

Run:
- `node --test --experimental-strip-types frontend/tests/textareaAutosize.test.ts frontend/tests/knowledgeBasePagination.test.ts`
- `npm --prefix frontend run build`

Expected: PASS.

### Task 3: Remove sidebar collapse behavior

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/layouts/AppShell.tsx`
- Modify: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/styles/theme.css`

**Step 1: Write the failing check**

Use the current build as the red check after simplifying the component props.

**Step 2: Write minimal implementation**

- remove `collapsed` state and toggle wiring from `App.tsx`
- remove `collapsed` and `onToggleSidebar` props from `AppShell.tsx`
- remove collapsed branches, toggle button, and title from `Sidebar.tsx`
- remove obsolete collapse styles from `theme.css`

**Step 3: Run build to verify it passes**

Run: `npm --prefix frontend run build`
Expected: PASS.

### Task 4: Fixed sidebar and larger logo

**Files:**
- Modify: `frontend/src/styles/theme.css`
- Modify: `frontend/src/components/Sidebar.tsx`

**Step 1:** Use the frontend build as the red check.

**Step 2:** Update layout styles so:
- `.app-shell` fills the viewport
- `.app-main` owns vertical scrolling
- `.app-sidebar` remains pinned within the viewport
- `.app-sidebar__top` stays full width
- `.sidebar-logo img` uses full available width with proportional height

**Step 3:** Re-run `npm --prefix frontend run build` and verify pass.

### Task 5: Homepage hero title move

**Files:**
- Modify: `frontend/src/pages/HomePage.tsx`
- Modify: `frontend/src/styles/theme.css`

**Step 1:** Use frontend build as the red check.

**Step 2:** Render `智能比对` as the homepage `h1` directly under `AI Assistant` and adjust spacing if needed.

**Step 3:** Re-run `npm --prefix frontend run build` and verify pass.

### Task 6: Final verification

**Files:**
- No new files required

**Step 1:** Run frontend unit tests.

```bash
node --test --experimental-strip-types frontend/tests/textareaAutosize.test.ts frontend/tests/knowledgeBasePagination.test.ts
```

**Step 2:** Run frontend build.

```bash
npm --prefix frontend run build
```

**Step 3:** Manually review the affected flows in code:
- sidebar has no collapse UI
- homepage hero includes `智能比对`
- KB textareas use the autosize path

Expected: tests pass, build passes, and affected files reflect the requested behavior.
