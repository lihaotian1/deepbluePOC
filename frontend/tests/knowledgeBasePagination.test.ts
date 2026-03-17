import assert from "node:assert/strict";
import test from "node:test";

import { buildKnowledgeBasePageModel } from "../src/pages/knowledgeBasePagination.ts";
import type { KnowledgeBaseDocument } from "../src/types.ts";

test("paginates grouped knowledge bases by item count instead of category count", () => {
  const document: KnowledgeBaseDocument = {
    file_name: "demo.json",
    display_name: "demo",
    format: "grouped",
    categories: [
      {
        name: "分类A",
        items: Array.from({ length: 11 }, (_, index) => ({
          text: `条目${index + 1}`,
          value: index % 2 === 0 ? "P" : "A",
        })),
      },
    ],
  };

  const firstPage = buildKnowledgeBasePageModel(document, "", 1, 10);
  const secondPage = buildKnowledgeBasePageModel(document, "", 2, 10);

  assert.equal(firstPage.totalEntries, 11);
  assert.equal(firstPage.totalPages, 2);
  assert.equal(firstPage.categories.length, 1);
  assert.equal(firstPage.categories[0].items.length, 10);
  assert.equal(firstPage.categories[0].items[0].itemIndex, 0);
  assert.equal(firstPage.categories[0].items[9].itemIndex, 9);

  assert.equal(secondPage.categories.length, 1);
  assert.equal(secondPage.categories[0].items.length, 1);
  assert.equal(secondPage.categories[0].items[0].itemIndex, 10);
});

test("keeps all items from a grouped category when the category name matches the search", () => {
  const document: KnowledgeBaseDocument = {
    file_name: "demo.json",
    display_name: "demo",
    format: "grouped",
    categories: [
      {
        name: "API 610",
        items: [
          { text: "Clause one", value: "P" },
          { text: "Clause two", value: "A" },
        ],
      },
      {
        name: "Other",
        items: [{ text: "Unrelated", value: "B" }],
      },
    ],
  };

  const result = buildKnowledgeBasePageModel(document, "api 610", 1, 10);

  assert.equal(result.totalEntries, 2);
  assert.equal(result.categories.length, 1);
  assert.equal(result.categories[0].items.length, 2);
  assert.deepEqual(
    result.categories[0].items.map((item) => item.item.text),
    ["Clause one", "Clause two"],
  );
});

test("treats each flat key-value pair as one paginated entry", () => {
  const document: KnowledgeBaseDocument = {
    file_name: "api610.json",
    display_name: "api610",
    format: "flat_key_value",
    categories: Array.from({ length: 11 }, (_, index) => ({
      name: `6.1.${index + 1}`,
      items: [{ text: `Clause ${index + 1}`, value: "" }],
    })),
  };

  const firstPage = buildKnowledgeBasePageModel(document, "", 1, 10);
  const secondPage = buildKnowledgeBasePageModel(document, "", 2, 10);

  assert.equal(firstPage.totalEntries, 11);
  assert.equal(firstPage.categories.length, 10);
  assert.equal(secondPage.categories.length, 1);
  assert.equal(secondPage.categories[0].name, "6.1.11");
});

test("does not let empty grouped categories consume pagination slots", () => {
  const document: KnowledgeBaseDocument = {
    file_name: "demo.json",
    display_name: "demo",
    format: "grouped",
    categories: [
      {
        name: "分类A",
        items: Array.from({ length: 10 }, (_, index) => ({
          text: `条目${index + 1}`,
          value: "P",
        })),
      },
      { name: "空分类", items: [] },
      { name: "另一个空分类", items: [] },
    ],
  };

  const result = buildKnowledgeBasePageModel(document, "", 1, 10);

  assert.equal(result.totalEntries, 10);
  assert.equal(result.totalPages, 1);
  assert.equal(result.categories.length, 1);
  assert.equal(result.categories[0].name, "分类A");
  assert.deepEqual(
    result.emptyCategories.map((category) => category.name),
    ["空分类", "另一个空分类"],
  );
});
