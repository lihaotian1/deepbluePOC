import { useEffect, useMemo, useState } from "react";

import {
  exportExcel,
  saveDocumentReviewState,
  translateChunkContent,
  uploadDocument,
} from "../api/client";
import { streamCompare } from "../api/sse";
import UploadPanel from "../components/UploadPanel";
import { buildTypeFilterModel, filterCompareRowsByType, mergeCompareRow } from "./homePageCompareState";
import {
  markCompareRowReviewed,
  normalizeCompareRow,
  removeCompareRow,
  updateCompareRowReviewComment,
} from "./homePageReviewState";
import type { CompareRow, ResultFilterType } from "../types";


const PAGE_SIZE = 10;

function HomePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [docId, setDocId] = useState("");
  const [documentText, setDocumentText] = useState("");
  const [compareRows, setCompareRows] = useState<CompareRow[]>([]);
  const [progressText, setProgressText] = useState("请上传文件");
  const [activeFilter, setActiveFilter] = useState<ResultFilterType>("ALL");
  const [page, setPage] = useState(1);
  const [submittedForReview, setSubmittedForReview] = useState(false);
  const [hasPendingReviewSync, setHasPendingReviewSync] = useState(false);
  const [previewExpanded, setPreviewExpanded] = useState(false);
  const [activeRowId, setActiveRowId] = useState("");
  const [translatedRowId, setTranslatedRowId] = useState("");
  const [translatedText, setTranslatedText] = useState("");
  const [translationError, setTranslationError] = useState("");
  const [translating, setTranslating] = useState(false);

  const filterModel = useMemo(() => buildTypeFilterModel(compareRows), [compareRows]);
  const filteredRows = useMemo(
    () => filterCompareRowsByType(compareRows, activeFilter),
    [activeFilter, compareRows],
  );
  const totalPages = Math.max(1, Math.ceil(filteredRows.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);
  const pagedRows = filteredRows.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);
  const activeRow = compareRows.find((row) => row.row_id === activeRowId) ?? null;
  const reviewedCount = compareRows.filter((row) => normalizeCompareRow(row).review_status === "已审").length;
  const displayExcerpt = activeRow && translatedRowId === activeRow.row_id && translatedText ? translatedText : activeRow?.source_excerpt ?? "";

  useEffect(() => {
    if (page !== safePage) {
      setPage(safePage);
    }
  }, [page, safePage]);

  useEffect(() => {
    if (activeRow && activeRow.row_id === translatedRowId) {
      return;
    }

    setTranslatedText("");
    setTranslationError("");
    setTranslatedRowId("");
    setTranslating(false);
  }, [activeRow, translatedRowId]);

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }

    setUploading(true);
    setProgressText("正在上传...");
    try {
      const response = await uploadDocument(selectedFile);
      setDocId(response.doc_id);
      setDocumentText(response.document_text);
      setCompareRows([]);
      setSubmittedForReview(false);
      setHasPendingReviewSync(false);
      setActiveFilter("ALL");
      setActiveRowId("");
      setPage(1);
      setPreviewExpanded(false);
      setProgressText("已准备就绪");
    } catch (error) {
      setProgressText("上传失败，请检查后重试");
    } finally {
      setUploading(false);
    }
  }

  async function handleCompare() {
    if (!docId) {
      return;
    }

    setComparing(true);
    setCompareRows([]);
    setSubmittedForReview(false);
    setHasPendingReviewSync(false);
    setActiveFilter("ALL");
    setActiveRowId("");
    setPage(1);
    setProgressText("正在解析...");

    try {
      await streamCompare(
        docId,
        (eventName, payload) => {
          const eventPayload = (payload || {}) as Record<string, unknown>;
          if (eventName === "compare_started") {
            setProgressText("正在解析...");
            return;
          }

          if (eventName === "compare_row") {
            const result = eventPayload.result as CompareRow | undefined;
            if (!result || typeof result.row_id !== "string") {
              return;
            }

            const normalizedRow = normalizeCompareRow(result);
            setCompareRows((prev) => mergeCompareRow(prev, normalizedRow));
            setProgressText("正在解析...");
            return;
          }

          if (eventName === "compare_done") {
            const rowCount = Number(eventPayload.row_count || 0);
            setProgressText(rowCount ? `已生成 ${rowCount} 条结果` : "未识别到可提示条目");
            return;
          }

          if (eventName === "error") {
            const message = String(eventPayload.message || "未知错误");
            setProgressText(message || "解析失败，请重试");
          }
        },
        () => undefined,
      );
    } catch (error) {
      const message = error instanceof Error && error.message ? error.message : "解析失败，请重试";
      setProgressText(message);
    } finally {
      setComparing(false);
    }
  }

  async function syncReviewState(nextSubmittedForReview: boolean) {
    if (!docId) {
      return;
    }

    const response = await saveDocumentReviewState(docId, {
      compare_rows: compareRows.map((row) => normalizeCompareRow(row)),
      submitted_for_review: nextSubmittedForReview,
    });
    setCompareRows(response.compare_rows.map((row) => normalizeCompareRow(row)));
    setSubmittedForReview(response.submitted_for_review);
    setHasPendingReviewSync(false);
  }

  async function handleExport() {
    if (!docId) {
      return;
    }

    try {
      if (hasPendingReviewSync) {
        setProgressText("正在保存...");
        await syncReviewState(submittedForReview);
      }

      setProgressText("正在导出...");
      const blob = await exportExcel(docId);
      const href = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = href;
      anchor.download = `${docId}_compare.xlsx`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(href);
      setProgressText("Excel 导出完成");
    } catch {
      setProgressText("导出失败，请重试");
    }
  }

  async function handleSubmitReview() {
    if (!docId) {
      return;
    }

    try {
      setProgressText("正在提交...");
      await syncReviewState(true);
      setProgressText("已提交");
    } catch {
      setProgressText("提交失败，请重试");
    }
  }

  function updateRow(rowId: string, updater: (row: CompareRow) => CompareRow) {
    setCompareRows((prev) => prev.map((row) => (row.row_id === rowId ? normalizeCompareRow(updater(normalizeCompareRow(row))) : row)));
    setHasPendingReviewSync(true);
    setSubmittedForReview(false);
  }

  function handleReviewCommentChange(rowId: string, value: string) {
    updateRow(rowId, (row) => updateCompareRowReviewComment(row, value));
  }

  function handleMarkReviewed(rowId: string) {
    updateRow(rowId, (row) => markCompareRowReviewed(row));
  }

  function handleDeleteRow(rowId: string) {
    setCompareRows((prev) => removeCompareRow(prev, rowId));
    setHasPendingReviewSync(true);
    setSubmittedForReview(false);
    if (activeRowId === rowId) {
      setActiveRowId("");
    }
  }

  async function handleTranslateActiveRow() {
    if (!activeRow || translating) {
      return;
    }

    if (translatedRowId === activeRow.row_id && translatedText) {
      setTranslatedRowId("");
      setTranslatedText("");
      setTranslationError("");
      return;
    }

    setTranslating(true);
    setTranslationError("");
    try {
      const response = await translateChunkContent(activeRow.source_excerpt);
      setTranslatedRowId(activeRow.row_id);
      setTranslatedText(response.translation);
    } catch {
      setTranslationError("翻译失败，请重试");
    } finally {
      setTranslating(false);
    }
  }

  return (
    <section className="page-shell page-shell--light">
      <section className="hero">
        <p className="hero__eyebrow">DeepBlue</p>
        <h1>询价文件标准化配套比对工作台</h1>
      </section>

      <UploadPanel loading={uploading} fileName={selectedFile?.name || ""} onSelectFile={setSelectedFile} onSubmit={handleUpload} />

      <section className="glass-card compare-panel compare-panel--light">
        <div className="compare-panel__head">
          <h2>智能分析</h2>
        </div>
        <div className="compare-panel__actions">
          <button className="btn btn-primary compare-panel__action-btn" onClick={handleCompare} disabled={!docId || comparing}>
            {comparing ? "解析中..." : "开始分析"}
          </button>
          <button className="btn btn-lite compare-panel__action-btn" onClick={handleExport} disabled={!docId || comparing}>
            导出 Excel
          </button>
          <button className="btn btn-review compare-panel__action-btn" onClick={handleSubmitReview} disabled={!docId || comparing}>
            提交审核
          </button>
          {submittedForReview ? <span className="compare-panel__submitted">已提交</span> : null}
        </div>
        <div className="compare-panel__status compare-panel__status--light">
          <span className="pulse-dot pulse-dot--static" />
          <span>{progressText}</span>
          <span className="compare-panel__status-meta">已审 {reviewedCount}/{compareRows.length}</span>
        </div>
      </section>

      <section className="glass-card filter-panel filter-panel--light">
        <div className="filter-panel__head">
          <div>
            <h3>分类筛选</h3>
          </div>
          <button className="btn btn-lite" type="button" onClick={() => setPreviewExpanded((prev) => !prev)} disabled={!documentText}>
            {previewExpanded ? "收起全文" : "查看全文"}
          </button>
        </div>
        <div className="filter-panel__buttons">
          {filterModel.order.map((filterKey) => (
            <button
              key={filterKey}
              type="button"
              className={`btn btn-lite filter-btn ${activeFilter === filterKey ? "is-active" : ""}`}
              onClick={() => {
                setActiveFilter(filterKey);
                setPage(1);
              }}
            >
              {filterModel.labels[filterKey]}({filterModel.counts[filterKey] ?? 0})
            </button>
          ))}
        </div>
      </section>

      {previewExpanded && documentText ? (
        <section className="glass-card document-preview">
          <div className="document-preview__head">
            <h3>询价文件全文</h3>
            <span>{selectedFile?.name || "已上传文件"}</span>
          </div>
          <pre className="document-preview__body">{documentText}</pre>
        </section>
      ) : null}

      <section className="glass-card results-table-card">
        <div className="results-table-card__head">
          <h2>命中结果</h2>
        </div>

        {!compareRows.length ? (
          <div className="results-empty">
            <p>{docId ? "尚未生成命中结果。" : "请先上传文件。"}</p>
          </div>
        ) : (
          <>
            <div className="results-table-wrap">
              <table className="results-table">
                <thead>
                  <tr>
                    <th>章节标题</th>
                    <th>询价文件的原文段落或句子</th>
                    <th>知识库标准化配套条目的原文</th>
                    <th>大模型总结的差异结论</th>
                    <th>分类</th>
                  </tr>
                </thead>
                <tbody>
                  {pagedRows.map((row) => (
                    <tr key={row.row_id} className={activeRowId === row.row_id ? "is-active" : ""} onClick={() => setActiveRowId(row.row_id)}>
                      <td>
                        <strong>{row.chapter_title}</strong>
                        <span className={`review-status review-status--${normalizeCompareRow(row).review_status === "已审" ? "done" : "pending"}`}>
                          {normalizeCompareRow(row).review_status}
                        </span>
                      </td>
                      <td>{row.source_excerpt}</td>
                      <td>{row.kb_entry_text}</td>
                      <td>
                        <span className={`summary-tone summary-tone--${resolveSummaryTone(row.difference_summary)}`}>{row.difference_summary}</span>
                      </td>
                      <td>
                        <span className={`table-type-pill table-type-pill--${row.type_code.toLowerCase()}`}>{row.type_code}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="kb-pagination-bar">
              <span>
                当前第 {safePage}/{totalPages} 页，共 {filteredRows.length} 条
              </span>
              <div className="kb-pagination-bar__actions">
                <button className="btn btn-lite" type="button" onClick={() => setPage((prev) => Math.max(1, prev - 1))} disabled={safePage <= 1}>
                  上一页
                </button>
                <button className="btn btn-lite" type="button" onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))} disabled={safePage >= totalPages}>
                  下一页
                </button>
              </div>
            </div>
          </>
        )}
      </section>

      {activeRow ? (
        <>
          <div className="drawer-backdrop" onClick={() => setActiveRowId("")} aria-hidden="true" />
          <aside className="result-drawer" aria-label="结果审核抽屉">
            <div className="result-drawer__head">
              <div>
                <p className="hero__eyebrow">审核详情</p>
                <h3>{activeRow.chapter_title}</h3>
              </div>
              <button className="btn btn-lite btn--tiny" type="button" onClick={() => setActiveRowId("")}>
                关闭
              </button>
            </div>

            <div className="result-drawer__section">
              <span className="muted">询价文件原文</span>
              <div className="result-drawer__excerpt">{displayExcerpt}</div>
              <div className="result-drawer__actions">
                <button className="btn btn-lite btn--tiny" type="button" onClick={() => void handleTranslateActiveRow()} disabled={translating}>
                  {translatedRowId === activeRow.row_id && translatedText ? "显示原文" : translating ? "翻译中..." : "翻译句段"}
                </button>
                <span className={`table-type-pill table-type-pill--${activeRow.type_code.toLowerCase()}`}>{activeRow.type_code}</span>
              </div>
              {translationError ? <p className="result-drawer__error">{translationError}</p> : null}
            </div>

            <div className="result-drawer__section">
              <span className="muted">标准化配套条目</span>
              <div className="result-drawer__excerpt">{activeRow.kb_entry_text}</div>
            </div>

            <div className="result-drawer__section">
              <span className="muted">差异结论</span>
              <div className={`summary-tone summary-tone--${resolveSummaryTone(activeRow.difference_summary)}`}>{activeRow.difference_summary}</div>
            </div>

            <div className="result-drawer__section">
              <label className="review-modal__field">
                <span>审核意见</span>
                <textarea
                  className="kb-input kb-input--textarea result-drawer__textarea"
                  rows={5}
                  value={activeRow.review_comment}
                  onChange={(event) => handleReviewCommentChange(activeRow.row_id, event.target.value)}
                />
              </label>
            </div>

            <div className="result-drawer__footer">
              <button className="btn btn-review" type="button" onClick={() => handleMarkReviewed(activeRow.row_id)}>
                标记已审
              </button>
              <button className="btn btn-lite kb-danger" type="button" onClick={() => handleDeleteRow(activeRow.row_id)}>
                删除结果
              </button>
            </div>
          </aside>
        </>
      ) : null}
    </section>
  );
}

function resolveSummaryTone(summary: string) {
  if (summary.startsWith("直接满足：")) {
    return "match";
  }
  if (summary.startsWith("存在冲突：")) {
    return "conflict";
  }
  return "partial";
}

export default HomePage;
