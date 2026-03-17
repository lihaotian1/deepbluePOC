import type { KnowledgeBaseCategory, KnowledgeBaseDocument, KnowledgeBaseItem } from "../types";

export interface EditableKnowledgeBaseItem extends KnowledgeBaseItem {
  clientId: string;
}

export interface EditableKnowledgeBaseCategory extends Omit<KnowledgeBaseCategory, "items"> {
  clientId: string;
  items: EditableKnowledgeBaseItem[];
}

export interface EditableKnowledgeBaseDocument extends Omit<KnowledgeBaseDocument, "categories"> {
  categories: EditableKnowledgeBaseCategory[];
}

export type KnowledgeBaseIdGenerator = () => string;

export function createKnowledgeBaseIdGenerator(prefix = "kb") {
  let nextId = 0;

  return () => `${prefix}-${nextId++}`;
}

export function withEditableKnowledgeBaseIds(
  document: KnowledgeBaseDocument,
  createId: KnowledgeBaseIdGenerator,
): EditableKnowledgeBaseDocument {
  return {
    ...document,
    categories: document.categories.map((category) => ({
      ...category,
      clientId: createId(),
      items: toEditableItems(category.items, document.format, createId),
    })),
  };
}

export function addEditableCategory(
  document: EditableKnowledgeBaseDocument,
  createId: KnowledgeBaseIdGenerator,
): EditableKnowledgeBaseDocument {
  const seed =
    document.format === "flat_key_value"
      ? `${document.categories.length + 1}`
      : `新分类${document.categories.length + 1}`;

  return {
    ...document,
    categories: [
      ...document.categories,
      {
        clientId: createId(),
        name: seed,
        items: [{ clientId: createId(), text: "", value: "" }],
      },
    ],
  };
}

export function updateEditableCategoryName(
  document: EditableKnowledgeBaseDocument,
  categoryId: string,
  value: string,
): EditableKnowledgeBaseDocument {
  return {
    ...document,
    categories: document.categories.map((category) =>
      category.clientId === categoryId ? { ...category, name: value } : category,
    ),
  };
}

export function removeEditableCategory(
  document: EditableKnowledgeBaseDocument,
  categoryId: string,
): EditableKnowledgeBaseDocument {
  return {
    ...document,
    categories: document.categories.filter((category) => category.clientId !== categoryId),
  };
}

export function addEditableItem(
  document: EditableKnowledgeBaseDocument,
  categoryId: string,
  createId: KnowledgeBaseIdGenerator,
): EditableKnowledgeBaseDocument {
  if (document.format === "flat_key_value") {
    return document;
  }

  return {
    ...document,
    categories: document.categories.map((category) =>
      category.clientId === categoryId
        ? {
            ...category,
            items: [...category.items, { clientId: createId(), text: "", value: "" }],
          }
        : category,
    ),
  };
}

export function updateEditableItem(
  document: EditableKnowledgeBaseDocument,
  categoryId: string,
  itemId: string,
  field: "text" | "value",
  value: string,
): EditableKnowledgeBaseDocument {
  return {
    ...document,
    categories: document.categories.map((category) => {
      if (category.clientId !== categoryId) {
        return category;
      }

      return {
        ...category,
        items: category.items.map((item) =>
          item.clientId === itemId ? { ...item, [field]: value } : item,
        ),
      };
    }),
  };
}

export function removeEditableItem(
  document: EditableKnowledgeBaseDocument,
  categoryId: string,
  itemId: string,
): EditableKnowledgeBaseDocument {
  if (document.format === "flat_key_value") {
    return document;
  }

  return {
    ...document,
    categories: document.categories.map((category) =>
      category.clientId === categoryId
        ? { ...category, items: category.items.filter((item) => item.clientId !== itemId) }
        : category,
    ),
  };
}

export function stripEditableKnowledgeBaseDocument(
  document: EditableKnowledgeBaseDocument,
): KnowledgeBaseDocument {
  return {
    ...document,
    categories: document.categories.map(({ clientId: _categoryId, items, ...category }) => ({
      ...category,
      items: items.map(({ clientId: _itemId, ...item }) => item),
    })),
  };
}

function toEditableItems(
  items: KnowledgeBaseItem[],
  format: KnowledgeBaseDocument["format"],
  createId: KnowledgeBaseIdGenerator,
) {
  if (format === "flat_key_value" && items.length === 0) {
    return [{ clientId: createId(), text: "", value: "" }];
  }

  return items.map((item) => ({ ...item, clientId: createId() }));
}
