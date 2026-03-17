import { useEffect, useMemo, useRef, useState } from "react";

import {
  createKnowledgeBaseDocument,
  deleteKnowledgeBaseDocument,
  getKnowledgeBaseDocument,
  saveKnowledgeBaseDocument,
} from "../api/client";
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
import { autosizeTextarea } from "../utils/textareaAutosize";
import { buildKnowledgeBasePageModel } from "./knowledgeBasePagination";
import type { EditableKnowledgeBaseDocument } from "./knowledgeBaseEditor";
import type { KnowledgeBaseCategory, KnowledgeBaseDocument } from "../types";


const PAGE_SIZE = 10;
const KB_TEXTAREA_MIN_HEIGHT = 44;

interface KnowledgeBasePageProps {
  selectedFile: string;
  onSelectFile: (fileName: string) => void;
  onFilesChanged: (preferredFile?: string) => Promise<void> | void;
}

function KnowledgeBasePage({ selectedFile, onSelectFile, onFilesChanged }: KnowledgeBasePageProps) {
  const [document, setDocument] = useState<EditableKnowledgeBaseDocument | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [creating, setCreating] = useState(false);
  const [message, setMessage] = useState("请选择知识库文件");
  const [searchTerm, setSearchTerm] = useState("");
  const [page, setPage] = useState(1);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newFileName, setNewFileName] = useState("");
  const [newFileFormat, setNewFileFormat] = useState<"grouped" | "flat_key_value">("grouped");
  const textareaRefs = useRef<Record<string, HTMLTextAreaElement | null>>({});
  const createClientId = useRef(createKnowledgeBaseIdGenerator()).current;

  useEffect(() => {
    if (!selectedFile) {
      setDocument(null);
      setMessage("请选择知识库文件");
      return;
    }

    let disposed = false;
    setLoading(true);
    setMessage("正在加载知识库...");
    setSearchTerm("");
    setPage(1);

    getKnowledgeBaseDocument(selectedFile)
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
  }, [selectedFile]);

  const isFlatDocument = document?.format === "flat_key_value";

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

  function handleTextareaChange(
    categoryId: string,
    itemId: string,
    field: "text" | "value",
    value: string,
    textarea?: HTMLTextAreaElement,
  ) {
    if (textarea) {
      autosizeTextarea(textarea, KB_TEXTAREA_MIN_HEIGHT);
    }

    updateItem(categoryId, itemId, field, value);
  }

  function updateCategoryName(categoryId: string, value: string) {
    setDocument((prev) => {
      if (!prev) {
        return prev;
      }

      return updateEditableCategoryName(prev, categoryId, value);
    });
  }

  function addCategory() {
    setDocument((prev) => {
      if (!prev) {
        return prev;
      }

      return addEditableCategory(prev, createClientId);
    });
  }

  function removeCategory(categoryId: string) {
    setDocument((prev) => {
      if (!prev) {
        return prev;
      }

      return removeEditableCategory(prev, categoryId);
    });
  }

  function addItem(categoryId: string) {
    setDocument((prev) => {
      if (!prev || prev.format === "flat_key_value") {
        return prev;
      }

      return addEditableItem(prev, categoryId, createClientId);
    });
  }

  function updateItem(categoryId: string, itemId: string, field: "text" | "value", value: string) {
    setDocument((prev) => {
      if (!prev) {
        return prev;
      }

      return updateEditableItem(prev, categoryId, itemId, field, value);
    });
  }

  function removeItem(categoryId: string, itemId: string) {
    setDocument((prev) => {
      if (!prev || prev.format === "flat_key_value") {
        return prev;
      }

      return removeEditableItem(prev, categoryId, itemId);
    });
  }

  async function handleSave() {
    if (!document) {
      return;
    }
    setSaving(true);
    setMessage("正在保存知识库...");
    try {
      const persisted = stripEditableKnowledgeBaseDocument(document);
      const sanitized: KnowledgeBaseDocument = {
        ...persisted,
        categories: persisted.categories
          .map((category) => sanitizeCategory(category, persisted.format))
          .filter((category) => category.name),
      };
      const saved = await saveKnowledgeBaseDocument(selectedFile, sanitized);
      setDocument(withEditableKnowledgeBaseIds(saved, createClientId));
      setMessage(`保存成功: ${saved.display_name}`);
    } catch (error) {
      setMessage(`保存失败: ${String(error)}`);
    } finally {
      setSaving(false);
    }
  }

  async function handleCreateFile() {
    const normalizedName = normalizeFileName(newFileName);
    if (!normalizedName) {
      setMessage("请输入知识库文件名");
      return;
    }

    setCreating(true);
    setMessage("正在创建知识库文件...");
    try {
      const created = await createKnowledgeBaseDocument({
        file_name: normalizedName,
        format: newFileFormat,
      });
      await onFilesChanged(created.file_name);
      onSelectFile(created.file_name);
      setShowCreateForm(false);
      setNewFileName("");
      setMessage(`已创建 ${created.display_name}`);
    } catch (error) {
      setMessage(`创建失败: ${String(error)}`);
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteFile() {
    if (!selectedFile) {
      return;
    }
    if (!window.confirm(`确认删除知识库文件 ${selectedFile} 吗？`)) {
      return;
    }

    setMessage("正在删除知识库文件...");
    try {
      await deleteKnowledgeBaseDocument(selectedFile);
      setDocument(null);
      await onFilesChanged();
      setMessage(`已删除 ${selectedFile}`);
    } catch (error) {
      setMessage(`删除失败: ${String(error)}`);
    }
  }

  return (
    <section className="page-shell">
      <section className="hero hero--compact">
        <p className="hero__eyebrow">Knowledge Base Studio</p>
        <h1>知识库结构化管理</h1>
        <p className="hero__desc">兼容分类树与 key-value 源格式，支持搜索、分页和文件级管理。</p>
      </section>

      <section className="glass-card kb-toolbar">
        <div>
          <h2>{selectedFile || "未选择知识库"}</h2>
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
          <button className="btn btn-lite" type="button" onClick={() => setShowCreateForm((prev) => !prev)}>
            {showCreateForm ? "取消新建" : "新建知识库"}
          </button>
          <button className="btn btn-lite kb-danger" type="button" onClick={handleDeleteFile} disabled={!selectedFile}>
            删除当前知识库
          </button>
          <button className="btn btn-primary" type="button" onClick={handleSave} disabled={!document || loading || saving}>
            {saving ? "保存中..." : "保存知识库"}
          </button>
        </div>
      </section>

      {showCreateForm ? (
        <section className="glass-card kb-create-panel">
          <input
            className="kb-input"
            value={newFileName}
            onChange={(event) => setNewFileName(event.target.value)}
            placeholder="输入文件名，如 my-kb.json"
          />
          <select
            className="kb-input kb-input--select"
            value={newFileFormat}
            onChange={(event) => setNewFileFormat(event.target.value as "grouped" | "flat_key_value")}
          >
            <option value="grouped">结构化知识库</option>
            <option value="flat_key_value">API610 标准型</option>
          </select>
          <button className="btn btn-primary" type="button" onClick={handleCreateFile} disabled={creating}>
            {creating ? "创建中..." : "确认创建"}
          </button>
        </section>
      ) : null}

      {!document ? (
        <section className="glass-card kb-empty-state">
          <p>{loading ? "加载中..." : "请从左侧知识库菜单中选择一个文件。"}</p>
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
              <button className="btn btn-lite" type="button" onClick={addCategory}>
                {isFlatDocument ? "新增章节" : "新增分类"}
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
                const categoryIndex = category.categoryIndex;
                const editableCategory = document.categories[categoryIndex];
                if (!editableCategory) {
                  return null;
                }

                const categoryId = editableCategory.clientId;
                const primaryEditableItem = editableCategory.items[0];

                return (
                  <article className="glass-card kb-category-card" key={categoryId}>
                    <div className="kb-category-card__head">
                      <input
                        className="kb-input kb-input--title"
                        value={category.name}
                        onChange={(event) => updateCategoryName(categoryId, event.target.value)}
                        placeholder={isFlatDocument ? "章节编号 / key" : "分类名称"}
                      />
                      <div className="kb-category-card__actions">
                        {!isFlatDocument ? (
                          <button className="btn btn-lite" type="button" onClick={() => addItem(categoryId)}>
                            新增条目
                          </button>
                        ) : null}
                        <button className="btn btn-lite kb-danger" type="button" onClick={() => removeCategory(categoryId)}>
                          删除{isFlatDocument ? "章节" : "分类"}
                        </button>
                      </div>
                    </div>

                    {isFlatDocument ? (
                      <div className="kb-flat-editor">
                        {primaryEditableItem ? (
                          <textarea
                            ref={(textarea) => setTextareaRef(primaryEditableItem.clientId, textarea)}
                            className="kb-input kb-input--textarea kb-input--textarea-fixed"
                            value={primaryEditableItem.text}
                            onChange={(event) =>
                              handleTextareaChange(categoryId, primaryEditableItem.clientId, "text", event.target.value, event.target)
                            }
                            placeholder="章节内容"
                            rows={1}
                          />
                        ) : null}
                      </div>
                    ) : (
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
                                  handleTextareaChange(categoryId, editableItem.clientId, "text", event.target.value, event.target)
                                }
                                placeholder="条目内容"
                                rows={1}
                              />
                              <input
                                className="kb-input kb-input--value"
                                value={editableItem.value}
                                onChange={(event) => updateItem(categoryId, editableItem.clientId, "value", event.target.value)}
                                placeholder="类型值，如 P / A / C"
                              />
                              <button className="btn btn-lite kb-danger" type="button" onClick={() => removeItem(categoryId, editableItem.clientId)}>
                                删除
                              </button>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </article>
                );
              })}
              {pageModel?.emptyCategories.map((category) => {
                const categoryIndex = category.categoryIndex;
                const editableCategory = document.categories[categoryIndex];
                if (!editableCategory) {
                  return null;
                }

                const categoryId = editableCategory.clientId;

                return (
                  <article className="glass-card kb-category-card" key={categoryId}>
                    <div className="kb-category-card__head">
                      <input
                        className="kb-input kb-input--title"
                        value={category.name}
                        onChange={(event) => updateCategoryName(categoryId, event.target.value)}
                        placeholder="分类名称"
                      />
                      <div className="kb-category-card__actions">
                        <button className="btn btn-lite" type="button" onClick={() => addItem(categoryId)}>
                          新增条目
                        </button>
                        <button className="btn btn-lite kb-danger" type="button" onClick={() => removeCategory(categoryId)}>
                          删除分类
                        </button>
                      </div>
                    </div>

                    <div className="kb-item-list">
                      <p className="kb-empty-inline">当前分类暂无条目，不计入分页，可继续重命名、删除或直接新增。</p>
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

function normalizeFileName(value: string) {
  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }
  return trimmed.endsWith(".json") ? trimmed : `${trimmed}.json`;
}

function sanitizeCategory(
  category: KnowledgeBaseCategory,
  format: "grouped" | "flat_key_value"
): KnowledgeBaseCategory {
  if (format === "flat_key_value") {
    return {
      ...category,
      name: category.name.trim(),
      items: [
        {
          text: category.items[0]?.text?.trim() || "",
          value: "",
        },
      ],
    };
  }

  return {
    ...category,
    name: category.name.trim(),
    items: category.items
      .filter((item) => item.text.trim())
      .map((item) => ({ text: item.text.trim(), value: item.value.trim() })),
  };
}

export default KnowledgeBasePage;
