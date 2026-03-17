import assert from "node:assert/strict";
import test from "node:test";

import {
  addEditableCategory,
  addEditableItem,
  createKnowledgeBaseIdGenerator,
  removeEditableCategory,
  removeEditableItem,
  stripEditableKnowledgeBaseDocument,
  withEditableKnowledgeBaseIds,
} from "../src/pages/knowledgeBaseEditor.ts";
import type { KnowledgeBaseDocument } from "../src/types.ts";

test("preserves existing client ids when categories are added or removed", () => {
  const document: KnowledgeBaseDocument = {
    file_name: "demo.json",
    display_name: "demo",
    format: "grouped",
    categories: [
      {
        name: "分类A",
        items: [{ text: "条目A", value: "P" }],
      },
      {
        name: "分类B",
        items: [{ text: "条目B", value: "A" }],
      },
    ],
  };

  const createId = createKnowledgeBaseIdGenerator("test-cat");
  const editable = withEditableKnowledgeBaseIds(document, createId);
  const originalSecondCategoryId = editable.categories[1].clientId;

  const withAddedCategory = addEditableCategory(editable, createId);
  const withRemovedFirstCategory = removeEditableCategory(withAddedCategory, editable.categories[0].clientId);

  assert.equal(withRemovedFirstCategory.categories[0].clientId, originalSecondCategoryId);
  assert.equal(withRemovedFirstCategory.categories[0].name, "分类B");
});

test("preserves existing client ids when items are added or removed", () => {
  const document: KnowledgeBaseDocument = {
    file_name: "demo.json",
    display_name: "demo",
    format: "grouped",
    categories: [
      {
        name: "分类A",
        items: [
          { text: "条目A", value: "P" },
          { text: "条目B", value: "A" },
        ],
      },
    ],
  };

  const createId = createKnowledgeBaseIdGenerator("test-item");
  const editable = withEditableKnowledgeBaseIds(document, createId);
  const categoryId = editable.categories[0].clientId;
  const originalSecondItemId = editable.categories[0].items[1].clientId;

  const withAddedItem = addEditableItem(editable, categoryId, createId);
  const withRemovedFirstItem = removeEditableItem(
    withAddedItem,
    categoryId,
    editable.categories[0].items[0].clientId,
  );

  assert.equal(withRemovedFirstItem.categories[0].items[0].clientId, originalSecondItemId);
  assert.equal(withRemovedFirstItem.categories[0].items[0].text, "条目B");
});

test("strips client ids before persisting editable knowledge-base documents", () => {
  const document: KnowledgeBaseDocument = {
    file_name: "flat.json",
    display_name: "flat",
    format: "flat_key_value",
    categories: [
      {
        name: "6.1",
        items: [{ text: "Clause", value: "" }],
      },
    ],
  };

  const editable = withEditableKnowledgeBaseIds(document, createKnowledgeBaseIdGenerator("test-strip"));
  const persisted = stripEditableKnowledgeBaseDocument(editable);

  assert.deepEqual(persisted, document);
  assert.ok(!("clientId" in persisted.categories[0]));
  assert.ok(!("clientId" in persisted.categories[0].items[0]));
});

test("adds one editable placeholder item for malformed flat categories with no items", () => {
  const document: KnowledgeBaseDocument = {
    file_name: "flat.json",
    display_name: "flat",
    format: "flat_key_value",
    categories: [
      {
        name: "6.1",
        items: [],
      },
    ],
  };

  const editable = withEditableKnowledgeBaseIds(document, createKnowledgeBaseIdGenerator("test-flat-empty"));

  assert.equal(editable.categories[0].items.length, 1);
  assert.deepEqual(editable.categories[0].items[0], {
    clientId: "test-flat-empty-1",
    text: "",
    value: "",
  });
});
