# Translation Dot Persistence Design

## Goal

Keep the translation success indicator visible after a chunk has been translated, even when the user toggles back from translated text to the original text.

## Chosen Approach

- Keep the existing translation cache model unchanged.
- Derive the static green dot from the presence of a reusable cached translation for the current source snapshot.
- Preserve current button behavior:
  - translated view -> button shows `原文`
  - original view with cached translation -> button shows `翻译`
- Preserve current invalidation behavior:
  - source edits clear the cached translation and hide the dot
  - failed translation requests do not show the dot
  - in-flight translation still uses the animated dot

## Files

- `frontend/src/components/chunkCardTranslationState.ts`
- `frontend/tests/chunkCardTranslationState.test.ts`

## Success Criteria

- A translated chunk keeps the static green dot while viewing either translated text or the original text.
- The dot still disappears when the source content changes or translation fails.
