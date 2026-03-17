import type { KnowledgeBaseDocument, KnowledgeBaseItem } from "../types";

export interface PagedKnowledgeBaseItem {
  itemIndex: number;
  item: KnowledgeBaseItem;
}

export interface PagedKnowledgeBaseCategory {
  categoryIndex: number;
  name: string;
  items: PagedKnowledgeBaseItem[];
}

export interface EmptyKnowledgeBaseCategory {
  categoryIndex: number;
  name: string;
}

export interface KnowledgeBasePageModel {
  categories: PagedKnowledgeBaseCategory[];
  emptyCategories: EmptyKnowledgeBaseCategory[];
  page: number;
  totalEntries: number;
  totalPages: number;
}

interface KnowledgeBaseEntry {
  categoryIndex: number;
  categoryName: string;
  itemIndex: number;
  item: KnowledgeBaseItem;
}

interface BuiltKnowledgeBaseEntries {
  emptyCategories: EmptyKnowledgeBaseCategory[];
  entries: KnowledgeBaseEntry[];
}

export function buildKnowledgeBasePageModel(
  document: KnowledgeBaseDocument,
  searchTerm: string,
  requestedPage: number,
  pageSize: number,
): KnowledgeBasePageModel {
  const { entries, emptyCategories } = buildEntries(document, searchTerm);
  const totalEntries = entries.length;
  const totalPages = Math.max(1, Math.ceil(totalEntries / pageSize));
  const page = Math.min(Math.max(requestedPage, 1), totalPages);
  const start = (page - 1) * pageSize;
  const pagedEntries = entries.slice(start, start + pageSize);

  return {
    categories: groupEntries(pagedEntries),
    emptyCategories,
    page,
    totalEntries,
    totalPages,
  };
}

function buildEntries(document: KnowledgeBaseDocument, searchTerm: string): BuiltKnowledgeBaseEntries {
  const query = searchTerm.trim().toLowerCase();
  const emptyCategories: EmptyKnowledgeBaseCategory[] = [];

  const entries = document.categories.reduce<KnowledgeBaseEntry[]>((entries, category, categoryIndex) => {
    const categoryMatches = !query || category.name.toLowerCase().includes(query);

    if (document.format === "flat_key_value") {
      const primaryItem = category.items[0] ?? { text: "", value: "" };
      if (!categoryMatches && !primaryItem.text.toLowerCase().includes(query)) {
        return entries;
      }
      entries.push({ categoryIndex, categoryName: category.name, itemIndex: 0, item: primaryItem });
      return entries;
    }

    if (category.items.length === 0) {
      if (categoryMatches) {
        emptyCategories.push({ categoryIndex, name: category.name });
      }
      return entries;
    }

    category.items.forEach((item, itemIndex) => {
      if (categoryMatches) {
        entries.push({ categoryIndex, categoryName: category.name, itemIndex, item });
        return;
      }

      const itemMatches = item.text.toLowerCase().includes(query) || item.value.toLowerCase().includes(query);
      if (itemMatches) {
        entries.push({ categoryIndex, categoryName: category.name, itemIndex, item });
      }
    });
    return entries;
  }, []);

  return { emptyCategories, entries };
}

function groupEntries(entries: KnowledgeBaseEntry[]): PagedKnowledgeBaseCategory[] {
  const grouped = new Map<number, PagedKnowledgeBaseCategory>();

  entries.forEach((entry) => {
    const existing = grouped.get(entry.categoryIndex);
    if (existing) {
      existing.items.push({ itemIndex: entry.itemIndex, item: entry.item });
      return;
    }

    grouped.set(entry.categoryIndex, {
      categoryIndex: entry.categoryIndex,
      name: entry.categoryName,
      items: [{ itemIndex: entry.itemIndex, item: entry.item }],
    });
  });

  return [...grouped.values()];
}
