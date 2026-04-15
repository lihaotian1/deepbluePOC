import { useEffect, useMemo, useRef, useState } from "react";

import { getKnowledgeBaseDocument, saveKnowledgeBaseDocument } from "../api/client";
import { autosizeTextarea } from "../utils/textareaAutosize";
import {
  addEditableCategory,
  addEditableItem,
  createKnowledgeBaseIdGenerator,
  removeEditableCategory,
  removeEditableItem,
  stripEditableKnowledgeBaseDocument,
  updateEditableCategoryName,
  updateEditableItem,
  withEditableKnowledgeBaseIds,
} from "./knowledgeBaseEditor";
import { buildKnowledgeBasePageModel } from "./knowledgeBasePagination";
import { STANDARD_KB_FILE_NAME } from "./homePageCompareState";
import type { EditableKnowledgeBaseDocument } from "./knowledgeBaseEditor";
import type { KnowledgeBaseCategory, KnowledgeBaseDocument } from "../types";


const PAGE_SIZE = 10;
const KB_TEXTAREA_MIN_HEIGHT = 44;

function KnowledgeBasePage() {
  const [document, setDocument] = useState<EditableKnowledgeBaseDocument | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("正在准备标准化配套知识库...");
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(1);
  const textareaRefs = useRef<Record<string, HTMLTextAreaElement | null>>({});
  const createClientId = useRef(createKnowledgeBaseIdGenerator()).current;

  useEffect(() => {
    let disposed = false;
    setLoading(true);
    setMessage("正在加载标准化配套知识库...");
    getKnowledgeBaseDocument(STANDARD_KB_FILE_NAME)
      .then((response) => {
        if (disposed) {
          return;
        }
        setDocument(withEditableKnowledgeBaseIds(response, createClientId));
        setMessage(`已加载 ${response.display_name}`);
      })
      .catch((error) => {
        if (disposed) {
          return;
        }
        setDocument(null);
        setMessage(`加载失败: ${String(error)}`);
      })
      .finally(() => {
        if (!disposed) {
          setLoading(false);
        }
      });

    return () => {
      disposed = true;
    };
  }, [createClientId]);

  const pageModel = useMemo(() => {
    if (!document) {
      return null;
    }
    return buildKnowledgeBasePageModel(document, searchTerm, page, PAGE_SIZE);
  }, [document, page, searchTerm]);

  const currentPage = pageModel?.page ?? page;
  const totalPages = pageModel?.totalPages ?? 1;
  const hasVisibleCategories = (pageModel?.categories.length ?? 0) > 0 || (pageModel?.emptyCategories.length ?? 0) > 0;

  useEffect(() => {
    if (pageModel && page !== pageModel.page) {
      setPage(pageModel.page);
    }
  }, [page, pageModel]);

  useEffect(() => {
    Object.values(textareaRefs.current).forEach((textarea) => {
      if (textarea) {
        autosizeTextarea(textarea, KB_TEXTAREA_MIN_HEIGHT);
      }
    });
  }, [document, pageModel]);

  function setTextareaRef(key: string, textarea: HTMLTextAreaElement | null) {
    if (!textarea) {
      delete textareaRefs.current[key];
      return;
    }

    textareaRefs.current[key] = textarea;
    autosizeTextarea(textarea, KB_TEXTAREA_MIN_HEIGHT);
  }

  function updateCategoryName(categoryId: string, value: string) {
    setDocument((prev) => (prev ? updateEditableCategoryName(prev, categoryId, value) : prev));
  }

  function addCategory() {
    setDocument((prev) => (prev ? addEditableCategory(prev, createClientId) : prev));
  }

  function removeCategory(categoryId: string) {
    setDocument((prev) => (prev ? removeEditableCategory(prev, categoryId) : prev));
  }

  function addItem(categoryId: string) {
    setDocument((prev) => (prev ? addEditableItem(prev, categoryId, createClientId) : prev));
  }

  function updateItem(categoryId: string, itemId: string, field: "text" | "value", value: string, textarea?: HTMLTextAreaElement) {
    if (textarea) {
      autosizeTextarea(textarea, KB_TEXTAREA_MIN_HEIGHT);
    }
    setDocument((prev) => (prev ? updateEditableItem(prev, categoryId, itemId, field, value) : prev));
  }

  function removeItem(categoryId: string, itemId: string) {
    setDocument((prev) => (prev ? removeEditableItem(prev, categoryId, itemId) : prev));
  }

  async function handleSave() {
    if (!document) {
      return;
    }

    setSaving(true);
    setMessage("正在保存标准化配套知识库...");
    try {
      const persisted = stripEditableKnowledgeBaseDocument(document);
      const sanitized: KnowledgeBaseDocument = {
        ...persisted,
        categories: persisted.categories
          .map((category) => sanitizeCategory(category))
          .filter((category) => category.name),
      };
      const saved = await saveKnowledgeBaseDocument(STANDARD_KB_FILE_NAME, sanitized);
      setDocument(withEditableKnowledgeBaseIds(saved, createClientId));
      setMessage(`保存成功: ${saved.display_name}`);
    } catch (error) {
      setMessage(`保存失败: ${String(error)}`);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="page-shell">
      <section className="hero hero--compact">
        <p className="hero__eyebrow">Knowledge Base</p>
        <h1>标准化配套知识库</h1>
        <p className="hero__desc">仅保留标准化配套知识库维护入口，用于编辑条目内容与 P/A/B/C 分类。</p>
      </section>

      <section className="glass-card kb-toolbar">
        <div>
          <h2>{STANDARD_KB_FILE_NAME}</h2>
          <p>{message}</p>
        </div>
        <div className="kb-toolbar__actions">
          <input
            className="kb-input kb-input--search"
            value={searchTerm}
            onChange={(event) => {
              setSearchTerm(event.target.value);
              setPage(1);
            }}
            placeholder="搜索分类、条目或类型"
            disabled={!document}
          />
          <button className="btn btn-lite" type="button" onClick={addCategory} disabled={!document}>
            新增分类
          </button>
          <button className="btn btn-primary" type="button" onClick={handleSave} disabled={!document || loading || saving}>
            {saving ? "保存中..." : "保存知识库"}
          </button>
        </div>
      </section>

      {!document ? (
        <section className="glass-card kb-empty-state">
          <p>{loading ? "加载中..." : "无法读取标准化配套知识库。"}</p>
        </section>
      ) : (
        <>
          <section className="kb-pagination-bar">
            <span>
              共 {pageModel?.totalEntries ?? 0} 条，当前第 {currentPage}/{totalPages} 页
            </span>
            <div className="kb-pagination-bar__actions">
              <button className="btn btn-lite" type="button" onClick={() => setPage((prev) => Math.max(1, prev - 1))} disabled={currentPage <= 1}>
                上一页
              </button>
              <button className="btn btn-lite" type="button" onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))} disabled={currentPage >= totalPages}>
                下一页
              </button>
            </div>
          </section>

          {!hasVisibleCategories ? (
            <section className="glass-card kb-empty-state">
              <p>没有符合搜索条件的内容。</p>
            </section>
          ) : (
            <section className="kb-category-list">
              {pageModel?.categories.map((category) => {
                const editableCategory = document.categories[category.categoryIndex];
                if (!editableCategory) {
                  return null;
                }

                return (
                  <article className="glass-card kb-category-card" key={editableCategory.clientId}>
                    <div className="kb-category-card__head">
                      <input
                        className="kb-input kb-input--title"
                        value={category.name}
                        onChange={(event) => updateCategoryName(editableCategory.clientId, event.target.value)}
                        placeholder="分类名称"
                      />
                      <div className="kb-category-card__actions">
                        <button className="btn btn-lite" type="button" onClick={() => addItem(editableCategory.clientId)}>
                          新增条目
                        </button>
                        <button className="btn btn-lite kb-danger" type="button" onClick={() => removeCategory(editableCategory.clientId)}>
                          删除分类
                        </button>
                      </div>
                    </div>

                    <div className="kb-item-list">
                      {category.items.map(({ itemIndex }) => {
                        const editableItem = editableCategory.items[itemIndex];
                        if (!editableItem) {
                          return null;
                        }

                        return (
                          <div className="kb-item-row" key={editableItem.clientId}>
                            <textarea
                              ref={(textarea) => setTextareaRef(editableItem.clientId, textarea)}
                              className="kb-input kb-input--textarea kb-input--textarea-fixed"
                              value={editableItem.text}
                              onChange={(event) =>
                                updateItem(editableCategory.clientId, editableItem.clientId, "text", event.target.value, event.target)
                              }
                              placeholder="标准化配套条目原文"
                              rows={1}
                            />
                            <input
                              className="kb-input kb-input--value"
                              value={editableItem.value}
                              onChange={(event) => updateItem(editableCategory.clientId, editableItem.clientId, "value", event.target.value)}
                              placeholder="P / A / B / C"
                            />
                            <button className="btn btn-lite kb-danger" type="button" onClick={() => removeItem(editableCategory.clientId, editableItem.clientId)}>
                              删除
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </article>
                );
              })}
            </section>
          )}
        </>
      )}
    </section>
  );
}

function sanitizeCategory(category: KnowledgeBaseCategory): KnowledgeBaseCategory {
  return {
    ...category,
    name: category.name.trim(),
    items: category.items
      .filter((item) => item.text.trim())
      .map((item) => ({ text: item.text.trim(), value: item.value.trim() })),
  };
}

export default KnowledgeBasePage;
