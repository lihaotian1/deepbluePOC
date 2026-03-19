import { useEffect, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { createPortal } from "react-dom";

import { getKnowledgeBaseDocument, translateChunkContent } from "../api/client";
import type { Chunk, ChunkCompareResult, KnowledgeBaseDocument, KnowledgeBaseItem } from "../types";
import { autosizeTextarea } from "../utils/textareaAutosize";
import { TENDER_KB_FILE_NAME } from "../pages/homePageCompareState";
import {
  addManualReviewMatch,
  buildManualReviewMatch,
  getDefaultOtherReason,
  markChunkReviewed,
  normalizeReviewResult,
  removeReviewMatch,
  setOtherReviewOpinion,
  updateReviewMatchReason,
} from "../pages/homePageReviewState";
import {
  formatChunkCardTitle,
  getChunkCardViewState,
  resolveChunkCardCollapsedLineClamp,
  resolveChunkCardPanelOuterHeight,
  resolveChunkCardSynchronizedHeight,
} from "./chunkCardLayout";
import {
  buildSourceSentenceViewModels,
  getReasonHighlightPresentationState,
  getReasonHighlightResetKey,
  normalizeChunkCompareResultDisplay,
  splitChunkContentIntoSentences,
  toggleReasonHighlight,
} from "./chunkCardReasonHighlight";
import { resolveChunkSummaryTags } from "./chunkCardSummaryTags";
import {
  createChunkCardTranslationState,
  getChunkCardTranslationView,
  hasReusableChunkCardTranslation,
  invalidateChunkCardTranslation,
  receiveChunkCardTranslationFailure,
  receiveChunkCardTranslationSuccess,
  startChunkCardTranslation,
  toggleChunkCardTranslationView,
} from "./chunkCardTranslationState";
import { buildChunkCardHeaderActionGroups } from "./chunkCardHeaderViewState";
import { getChunkCardModalState } from "./chunkCardModalState";
import ResultTag from "./ResultTag";

const EDITOR_MIN_HEIGHT = 44;
const COLLAPSED_TAG_ROW_HEIGHT = 24;
const COLLAPSED_TAG_ROW_GAP = 8;
const COLLAPSED_PANEL_VERTICAL_INSET = 24;
const DEFAULT_COLLAPSED_TAG_AREA_HEIGHT = resolveChunkCardSynchronizedHeight({
  expanded: false,
  leftFullContentHeight: 0,
  rightDetailHeight: 0,
  measuredTagHeight: 0,
  tagRowHeight: COLLAPSED_TAG_ROW_HEIGHT,
  tagRowGap: COLLAPSED_TAG_ROW_GAP,
});
const COLLAPSED_SOURCE_LINE_HEIGHT = 24;

function lockGlobalModalScroll() {
  if (typeof document === "undefined") {
    return;
  }

  const body = document.body;
  const currentCount = Number(body.dataset.modalLockCount ?? "0");
  body.dataset.modalLockCount = `${currentCount + 1}`;
  body.classList.add("has-modal-open");
}

function unlockGlobalModalScroll() {
  if (typeof document === "undefined") {
    return;
  }

  const body = document.body;
  const currentCount = Number(body.dataset.modalLockCount ?? "0");
  const nextCount = Math.max(0, currentCount - 1);

  if (nextCount === 0) {
    delete body.dataset.modalLockCount;
    body.classList.remove("has-modal-open");
    return;
  }

  body.dataset.modalLockCount = `${nextCount}`;
}

function focusFirstModalElement(container: HTMLElement | null) {
  if (!container) {
    return;
  }

  const focusableElements = Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );

  if (focusableElements.length) {
    focusableElements[0].focus();
    return;
  }

  container.focus();
}

function trapFocusWithinModal(event: ReactKeyboardEvent<HTMLElement>, container: HTMLElement | null) {
  if (event.key !== "Tab" || !container) {
    return;
  }

  const focusableElements = Array.from(
    container.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  );

  if (!focusableElements.length) {
    event.preventDefault();
    container.focus();
    return;
  }

  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];
  const activeElement = document.activeElement;

  if (event.shiftKey && activeElement === firstElement) {
    event.preventDefault();
    lastElement.focus();
    return;
  }

  if (!event.shiftKey && activeElement === lastElement) {
    event.preventDefault();
    firstElement.focus();
  }
}

interface ChunkCardProps {
  chunk: Chunk;
  result?: ChunkCompareResult;
  activeKnowledgeBaseFile: string;
  onChange: (chunkId: number, value: string) => void;
  onReviewChange: (chunkId: number, result: ChunkCompareResult) => void;
}

function ChunkCard({ chunk, result, activeKnowledgeBaseFile, onChange, onReviewChange }: ChunkCardProps) {
  const [mode, setMode] = useState<"preview" | "edit">("preview");
  const [expandResult, setExpandResult] = useState(false);
  const [activeReasonHighlight, setActiveReasonHighlight] = useState<{
    reasonKey: string;
    sentenceIndex: number;
  } | null>(null);
  const editorRef = useRef<HTMLTextAreaElement | null>(null);
  const collapsedTagAreaRef = useRef<HTMLDivElement | null>(null);
  const reviewModalRef = useRef<HTMLElement | null>(null);
  const addModalRef = useRef<HTMLElement | null>(null);
  const [collapsedTagAreaHeight, setCollapsedTagAreaHeight] = useState(DEFAULT_COLLAPSED_TAG_AREA_HEIGHT);
  const [translationState, setTranslationState] = useState(createChunkCardTranslationState);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [knowledgeBaseDocument, setKnowledgeBaseDocument] = useState<KnowledgeBaseDocument | null>(null);
  const [knowledgeBaseLoading, setKnowledgeBaseLoading] = useState(false);
  const [knowledgeBaseError, setKnowledgeBaseError] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [selectedEntryKey, setSelectedEntryKey] = useState("");
  const [reviewOpinion, setReviewOpinion] = useState("");
  const [reviewValidationMessage, setReviewValidationMessage] = useState("");

  const viewState = useMemo(() => getChunkCardViewState({ expanded: expandResult }), [expandResult]);
  const title = useMemo(() => formatChunkCardTitle(chunk.heading), [chunk.heading]);
  const sourceSentences = useMemo(() => splitChunkContentIntoSentences(chunk.content), [chunk.content]);
  const reviewedResult = useMemo(() => (result ? normalizeReviewResult(result) : undefined), [result]);
  const reasonHighlightResetKey = useMemo(
    () => getReasonHighlightResetKey(chunk.content, reviewedResult),
    [chunk.content, reviewedResult],
  );
  const compareDisplayState = useMemo(() => normalizeChunkCompareResultDisplay(reviewedResult), [reviewedResult]);
  const sourceSentenceViewModels = useMemo(
    () => buildSourceSentenceViewModels(sourceSentences, activeReasonHighlight),
    [activeReasonHighlight, sourceSentences],
  );
  const resultTypeCodes = compareDisplayState.resultTypeCodes;
  const summaryTags = useMemo(() => resolveChunkSummaryTags(reviewedResult), [reviewedResult]);
  const collapsedLineClamp = resolveChunkCardCollapsedLineClamp({
    synchronizedContentHeight: collapsedTagAreaHeight,
    lineHeight: COLLAPSED_SOURCE_LINE_HEIGHT,
  });
  const collapsedPanelHeight = resolveChunkCardPanelOuterHeight({
    synchronizedContentHeight: collapsedTagAreaHeight,
    panelVerticalInset: COLLAPSED_PANEL_VERTICAL_INSET,
  });
  const isPreviewCollapsed = mode === "preview" && viewState.leftContentMode === "truncated";
  const synchronizedPreviewStyle = isPreviewCollapsed ? { height: `${collapsedPanelHeight}px` } : undefined;
  const resultToggleText = expandResult ? "收起" : "展开";
  const translationView = useMemo(
    () => getChunkCardTranslationView(translationState, chunk.content),
    [chunk.content, translationState],
  );
  const isShowingTranslation = translationView.buttonText === "原文";
  const isReviewed = reviewedResult?.review_status === "已审";
  const categoryNames = useMemo(() => {
    const names = knowledgeBaseDocument?.categories.map((category) => category.name) ?? [];
    return [...names, "其他"];
  }, [knowledgeBaseDocument]);
  const selectedCategoryItems = useMemo(() => {
    if (!knowledgeBaseDocument || !selectedCategory || selectedCategory === "其他") {
      return [];
    }
    return knowledgeBaseDocument.categories.find((category) => category.name === selectedCategory)?.items ?? [];
  }, [knowledgeBaseDocument, selectedCategory]);
  const selectedKnowledgeBaseItem = useMemo(() => {
    if (!selectedEntryKey) {
      return null;
    }
    const selectedIndex = Number(selectedEntryKey);
    return Number.isInteger(selectedIndex) && selectedIndex >= 0 ? selectedCategoryItems[selectedIndex] ?? null : null;
  }, [selectedCategoryItems, selectedEntryKey]);
  const modalState = useMemo(
    () => getChunkCardModalState({ isReviewModalOpen, isAddModalOpen }),
    [isAddModalOpen, isReviewModalOpen],
  );
  const headerActionGroups = useMemo(
    () => buildChunkCardHeaderActionGroups({ mode, isReviewed }),
    [isReviewed, mode],
  );

  useEffect(() => {
    if (mode !== "edit" || !editorRef.current) {
      return;
    }

    autosizeTextarea(editorRef.current, EDITOR_MIN_HEIGHT);
  }, [chunk.content, mode]);

  useEffect(() => {
    if (mode !== "preview" || viewState.rightContentMode !== "tags-only") {
      return;
    }

    const tagArea = collapsedTagAreaRef.current;
    if (!tagArea) {
      return;
    }

    const updateCollapsedHeight = () => {
      const nextHeight = resolveChunkCardSynchronizedHeight({
        expanded: false,
        leftFullContentHeight: 0,
        rightDetailHeight: 0,
        measuredTagHeight: Math.ceil(tagArea.getBoundingClientRect().height),
        tagRowHeight: COLLAPSED_TAG_ROW_HEIGHT,
        tagRowGap: COLLAPSED_TAG_ROW_GAP,
      });

      setCollapsedTagAreaHeight((currentHeight) => (currentHeight === nextHeight ? currentHeight : nextHeight));
    };

    updateCollapsedHeight();

    if (typeof ResizeObserver === "function") {
      const observer = new ResizeObserver(() => updateCollapsedHeight());
      observer.observe(tagArea);
      return () => observer.disconnect();
    }

    window.addEventListener("resize", updateCollapsedHeight);
    return () => window.removeEventListener("resize", updateCollapsedHeight);
  }, [mode, reviewedResult?.categories, reviewedResult?.label, reviewedResult?.matches.length, resultTypeCodes, viewState.rightContentMode]);

  useEffect(() => {
    setActiveReasonHighlight(null);
  }, [reasonHighlightResetKey]);

  useEffect(() => {
    setTranslationState((currentState) => invalidateChunkCardTranslation(currentState, chunk.content));
  }, [chunk.content]);

  useEffect(() => {
    if (reviewedResult) {
      return;
    }

    setIsReviewModalOpen(false);
    setIsAddModalOpen(false);
  }, [reviewedResult]);

  useEffect(() => {
    if (!isAddModalOpen) {
      return;
    }

    let disposed = false;
    setKnowledgeBaseLoading(true);
    setKnowledgeBaseError("");

    getKnowledgeBaseDocument(activeKnowledgeBaseFile)
      .then((document) => {
        if (disposed) {
          return;
        }
        setKnowledgeBaseDocument(document);
        const nextCategory = document.categories[0]?.name ?? "其他";
        setSelectedCategory(nextCategory);
        setSelectedEntryKey("");
        setReviewOpinion(nextCategory === "其他" ? getDefaultOtherReason() : "");
      })
      .catch((error) => {
        if (disposed) {
          return;
        }
        setKnowledgeBaseDocument(null);
        setKnowledgeBaseError(`知识库加载失败: ${String(error)}`);
        setSelectedCategory("其他");
        setReviewOpinion(getDefaultOtherReason());
      })
      .finally(() => {
        if (!disposed) {
          setKnowledgeBaseLoading(false);
        }
      });

    return () => {
      disposed = true;
    };
  }, [activeKnowledgeBaseFile, isAddModalOpen]);

  useEffect(() => {
    if (!isAddModalOpen) {
      return;
    }

    setSelectedEntryKey("");
    setReviewValidationMessage("");
    setReviewOpinion(selectedCategory === "其他" ? getDefaultOtherReason() : "");
  }, [isAddModalOpen, selectedCategory]);

  useEffect(() => {
    if (!modalState.shouldLockBackgroundScroll) {
      return;
    }

    lockGlobalModalScroll();
    return () => unlockGlobalModalScroll();
  }, [modalState.shouldLockBackgroundScroll]);

  useEffect(() => {
    const reviewModalElement = reviewModalRef.current;
    if (!reviewModalElement) {
      return;
    }

    if (modalState.isReviewModalInert) {
      reviewModalElement.setAttribute("inert", "");
      return () => reviewModalElement.removeAttribute("inert");
    }

    reviewModalElement.removeAttribute("inert");
  }, [modalState.isReviewModalInert, isReviewModalOpen]);

  useEffect(() => {
    if (modalState.activeModalKey === "add") {
      focusFirstModalElement(addModalRef.current);
      return;
    }

    if (modalState.activeModalKey === "review") {
      focusFirstModalElement(reviewModalRef.current);
    }
  }, [modalState.activeModalKey]);

  function handleReviewToggle() {
    if (!reviewedResult || isReviewed) {
      return;
    }

    onReviewChange(chunk.chunk_id, markChunkReviewed(reviewedResult));
  }

  function handleReasonChange(entryId: string, value: string) {
    if (!reviewedResult) {
      return;
    }

    onReviewChange(chunk.chunk_id, updateReviewMatchReason(reviewedResult, entryId, value));
  }

  function handleRemoveReviewMatch(entryId: string) {
    if (!reviewedResult) {
      return;
    }

    onReviewChange(chunk.chunk_id, removeReviewMatch(reviewedResult, entryId));
  }

  function handleOtherReasonChange(value: string) {
    if (!reviewedResult) {
      return;
    }

    onReviewChange(chunk.chunk_id, setOtherReviewOpinion(reviewedResult, value));
  }

  function resolveManualMatchTypeCode(item: KnowledgeBaseItem | null) {
    if (selectedCategory === "其他") {
      return "OTHER";
    }

    if (activeKnowledgeBaseFile === TENDER_KB_FILE_NAME) {
      return selectedCategory;
    }

    return item?.value?.trim() || "OTHER";
  }

  function handleConfirmAddReviewMatch() {
    if (!reviewedResult) {
      return;
    }

    if (selectedCategory !== "其他" && !selectedKnowledgeBaseItem) {
      setReviewValidationMessage("请选择一个知识库条目");
      return;
    }

    if (!reviewOpinion.trim()) {
      setReviewValidationMessage("请填写审核意见");
      return;
    }

    const displayText = selectedCategory === "其他" ? getDefaultOtherReason() : selectedKnowledgeBaseItem?.text ?? "";
    const nextMatch = buildManualReviewMatch({
      entryId: `manual-${activeKnowledgeBaseFile}-${chunk.chunk_id}-${Date.now()}`,
      category: selectedCategory || "其他",
      text: displayText,
      typeCode: resolveManualMatchTypeCode(selectedKnowledgeBaseItem),
      reason: reviewOpinion,
    });

    onReviewChange(chunk.chunk_id, addManualReviewMatch(reviewedResult, nextMatch));
    setIsAddModalOpen(false);
    setReviewValidationMessage("");
  }

  async function handleTranslationToggle() {
    if (translationState.isTranslating || !chunk.content.trim()) {
      return;
    }

    if (hasReusableChunkCardTranslation(translationState, chunk.content)) {
      setTranslationState((currentState) => toggleChunkCardTranslationView(currentState));
      return;
    }

    const sourceSnapshot = chunk.content;
    setTranslationState((currentState) => startChunkCardTranslation(currentState, sourceSnapshot));

    try {
      const response = await translateChunkContent(sourceSnapshot);
      setTranslationState((currentState) =>
        receiveChunkCardTranslationSuccess(currentState, {
          sourceSnapshot,
          translation: response.translation,
        }),
      );
    } catch {
      setTranslationState((currentState) =>
        receiveChunkCardTranslationFailure(currentState, {
          sourceSnapshot,
          message: "翻译失败，请重试",
        }),
      );
    }
  }

  const renderResultSummary = (ref?: typeof collapsedTagAreaRef) => {
    if (!reviewedResult) {
      return (
        <div className="chunk-result-panel__summary" ref={ref}>
          <span className="chunk-summary-pill chunk-summary-pill--pending">待智能分析</span>
        </div>
      );
    }

    if (compareDisplayState.state === "no-hit") {
      return (
        <div className="chunk-result-panel__summary" ref={ref}>
          <ResultTag code={summaryTags[0] ?? "OTHER"} />
          <span className="chunk-summary-pill">其他</span>
        </div>
      );
    }

    return (
      <div className="chunk-result-panel__summary" ref={ref}>
        <span className="chunk-summary-pill chunk-summary-pill--accent">命中 {reviewedResult.matches.length} 条</span>
        {summaryTags.map((code) => (
          <ResultTag key={code} code={code} />
        ))}
      </div>
    );
  };

  const reviewModal = isReviewModalOpen ? (
    <div
      className={modalState.reviewBackdropClassName}
      role="presentation"
      onClick={() => setIsReviewModalOpen(false)}
      onWheelCapture={(event) => event.stopPropagation()}
    >
      <section
        ref={reviewModalRef}
        className="modal-card review-modal"
        role="dialog"
        tabIndex={-1}
        aria-modal={!modalState.isReviewModalInert}
        aria-hidden={modalState.isReviewModalInert}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => trapFocusWithinModal(event, reviewModalRef.current)}
        onWheelCapture={(event) => event.stopPropagation()}
      >
        <div className="modal-card__head">
          <div>
            <h4>修改命中条目</h4>
            <p>{title}</p>
          </div>
          <div className="modal-card__actions">
            <button className="btn btn-secondary btn--tiny" type="button" onClick={() => setIsAddModalOpen(true)} disabled={!reviewedResult}>
              添加
            </button>
            <button className="btn btn-lite btn--tiny" type="button" onClick={() => setIsReviewModalOpen(false)}>
              关闭
            </button>
          </div>
        </div>

        <div className="review-modal__body">
          {compareDisplayState.state === "no-hit" ? (
            <div className="match-item">
              <div className="match-item__top review-modal__item-top">
                <div className="review-modal__item-tags">
                  <ResultTag code="OTHER" />
                  <span>其他</span>
                </div>
              </div>
              <p>{reviewedResult?.matches[0]?.text || getDefaultOtherReason()}</p>
              <label className="review-modal__field">
                <span>审核意见</span>
                <textarea
                  className="chunk-editor review-modal__textarea"
                  rows={4}
                  value={reviewedResult?.matches[0]?.reason ?? ""}
                  onChange={(event) => handleOtherReasonChange(event.target.value)}
                />
              </label>
            </div>
          ) : !reviewedResult?.matches.length ? (
            <div className="review-modal__empty">当前没有命中条目，可点击“添加”补充审核条目。</div>
          ) : (
            <div className="match-list">
              {reviewedResult.matches.map((item) => (
                <div className="match-item" key={item.entry_id}>
                  <div className="match-item__top review-modal__item-top">
                    <div className="review-modal__item-tags">
                      <ResultTag code={item.type_code} />
                      <span>{item.category}</span>
                    </div>
                    <button className="btn btn-lite btn--tiny" type="button" onClick={() => handleRemoveReviewMatch(item.entry_id)}>
                      删除
                    </button>
                  </div>
                  <p>{item.text || "未命中知识库条目，归类为其他。"}</p>
                  <label className="review-modal__field">
                    <span>审核意见</span>
                    <textarea
                      className="chunk-editor review-modal__textarea"
                      rows={4}
                      value={item.reason}
                      onChange={(event) => handleReasonChange(item.entry_id, event.target.value)}
                    />
                  </label>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  ) : null;

  const addModal = isAddModalOpen ? (
    <div
      className={modalState.addBackdropClassName}
      role="presentation"
      onClick={() => setIsAddModalOpen(false)}
      onWheelCapture={(event) => event.stopPropagation()}
    >
      <section
        ref={addModalRef}
        className="modal-card review-picker"
        role="dialog"
        aria-modal="true"
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={(event) => trapFocusWithinModal(event, addModalRef.current)}
        onWheelCapture={(event) => event.stopPropagation()}
      >
        <div className="modal-card__head">
          <div>
            <h4>添加审核条目</h4>
            <p>{activeKnowledgeBaseFile.replace(/\.json$/, "")}</p>
          </div>
          <button className="btn btn-lite btn--tiny" type="button" onClick={() => setIsAddModalOpen(false)}>
            关闭
          </button>
        </div>

        <div className="review-picker__layout">
          <div className="review-picker__top">
            <aside className="review-picker__categories">
              {categoryNames.map((categoryName) => (
                <button
                  key={categoryName}
                  className={`review-picker__category ${selectedCategory === categoryName ? "is-active" : ""}`}
                  type="button"
                  onClick={() => setSelectedCategory(categoryName)}
                >
                  {categoryName}
                </button>
              ))}
            </aside>

            <section className="review-picker__entries">
              {knowledgeBaseLoading ? <p className="review-picker__placeholder">正在加载知识库...</p> : null}
              {!knowledgeBaseLoading && knowledgeBaseError ? <p className="review-picker__error">{knowledgeBaseError}</p> : null}
              {!knowledgeBaseLoading && !knowledgeBaseError && selectedCategory === "其他" ? (
                <p className="review-picker__placeholder">“其他”分类无需选择知识库条目。</p>
              ) : null}
              {!knowledgeBaseLoading && !knowledgeBaseError && selectedCategory !== "其他" ? (
                selectedCategoryItems.length ? (
                  <div className="review-picker__entry-list">
                    {selectedCategoryItems.map((item, index) => (
                      <label className="review-picker__entry" key={`${selectedCategory}-${index}`}>
                        <input
                          type="radio"
                          name={`review-entry-${chunk.chunk_id}`}
                          checked={selectedEntryKey === `${index}`}
                          onChange={() => setSelectedEntryKey(`${index}`)}
                        />
                        <div>
                          <strong>{item.text}</strong>
                          <small>{item.value}</small>
                        </div>
                      </label>
                    ))}
                  </div>
                ) : (
                  <p className="review-picker__placeholder">当前分类下暂无条目。</p>
                )
              ) : null}
            </section>
          </div>

          <div className="review-picker__bottom">
            <label className="review-modal__field">
              <span>审核意见</span>
              <textarea
                className="chunk-editor review-picker__textarea"
                rows={4}
                value={reviewOpinion}
                onChange={(event) => {
                  setReviewOpinion(event.target.value);
                  setReviewValidationMessage("");
                }}
              />
            </label>

            <div className="review-picker__footer">
              {reviewValidationMessage ? <p className="review-picker__error">{reviewValidationMessage}</p> : <span className="muted">审核意见不能为空</span>}
              <div className="modal-card__actions">
                <button className="btn btn-lite btn--tiny" type="button" onClick={() => setIsAddModalOpen(false)}>
                  取消
                </button>
                <button className="btn btn-secondary btn--tiny" type="button" onClick={handleConfirmAddReviewMatch}>
                  确定
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  ) : null;

  return (
    <article className="glass-card chunk-card">
      <header className="chunk-card__header">
        <div
          className={headerActionGroups[0]?.containerClassName}
          style={headerActionGroups[0]?.titleGapPx ? { columnGap: `${headerActionGroups[0].titleGapPx}px` } : undefined}
        >
          <div className={headerActionGroups[0]?.titleContainerClassName}>
            <h3>{title}</h3>
            <p>Level {chunk.level} · Line {chunk.line_no}</p>
          </div>
          <div className={headerActionGroups[0]?.className}>
            <button className={headerActionGroups[0]?.actions[0]?.className} onClick={() => setMode("preview")} type="button">
              {headerActionGroups[0]?.actions[0]?.label}
            </button>
            <button className={headerActionGroups[0]?.actions[1]?.className} onClick={() => setMode("edit")} type="button">
              {headerActionGroups[0]?.actions[1]?.label}
            </button>
          </div>
        </div>
        <div className={headerActionGroups[1]?.containerClassName}>
          <div className={headerActionGroups[1]?.className}>
            <button
              className={headerActionGroups[1]?.actions[0]?.className}
              onClick={() => setIsReviewModalOpen(true)}
              type="button"
              disabled={!reviewedResult}
            >
              {headerActionGroups[1]?.actions[0]?.label}
            </button>
            <button
              className={headerActionGroups[1]?.actions[1]?.className}
              onClick={handleReviewToggle}
              type="button"
              disabled={!reviewedResult}
            >
              {headerActionGroups[1]?.actions[1]?.label}
            </button>
          </div>
        </div>
      </header>

      <section className="chunk-card__content chunk-card__content--row">
        <div className="chunk-panel">
          <div className="chunk-panel__head">
            <span className="muted">原文内容</span>
            {mode === "preview" ? (
              <div className="chunk-panel__actions">
                {translationView.statusDotMode !== "hidden" ? (
                  <span className={`pulse-dot${translationView.statusDotMode === "ready" ? " pulse-dot--static" : ""}`} />
                ) : null}
                <button
                  className="mini-toggle"
                  type="button"
                  onClick={() => void handleTranslationToggle()}
                  disabled={translationView.buttonDisabled}
                >
                  {translationView.buttonText}
                </button>
              </div>
            ) : null}
          </div>

          {translationView.errorMessage ? <p className="chunk-panel__error">{translationView.errorMessage}</p> : null}

          {mode === "edit" ? (
            <textarea
              ref={editorRef}
              value={chunk.content}
              onChange={(event) => {
                autosizeTextarea(event.target, EDITOR_MIN_HEIGHT);
                onChange(chunk.chunk_id, event.target.value);
              }}
              className="chunk-editor chunk-editor--auto"
              rows={1}
            />
          ) : viewState.leftContentMode === "truncated" ? (
            <div className="source-panel source-panel--truncated" style={synchronizedPreviewStyle}>
              <p
                className="source-panel__excerpt"
                style={{
                  WebkitLineClamp: collapsedLineClamp,
                  lineHeight: `${COLLAPSED_SOURCE_LINE_HEIGHT}px`,
                }}
              >
                {translationView.displayText}
              </p>
            </div>
          ) : (
            <div className="source-panel">
              <div className="source-panel__content">
                {isShowingTranslation
                  ? translationView.displayText
                  : sourceSentenceViewModels.map((sentence) => (
                      <span
                        key={sentence.index}
                        className={`source-panel__sentence${sentence.isActive ? " is-active" : ""}`}
                      >
                        {sentence.text}
                      </span>
                    ))}
                {!isShowingTranslation && !sourceSentenceViewModels.length ? chunk.content : null}
              </div>
            </div>
          )}
        </div>
        <div className="chunk-panel chunk-panel--result">
          <div className="chunk-panel__head">
            <span className="muted">知识库智能分析结果</span>
            <button className="mini-toggle" type="button" onClick={() => setExpandResult((prev) => !prev)}>
              {resultToggleText}
            </button>
          </div>

          <div
            className={`chunk-result-panel ${viewState.rightContentMode === "details" ? "is-expanded" : "is-collapsed"}`}
            style={synchronizedPreviewStyle}
          >
            {renderResultSummary(viewState.rightContentMode === "tags-only" ? collapsedTagAreaRef : undefined)}

            {viewState.rightContentMode === "details" ? (
              !reviewedResult ? null : compareDisplayState.state === "no-hit" ? (
                <div className="match-item">
                  <div className="match-item__top">
                    <ResultTag code="OTHER" />
                    <span>其他</span>
                  </div>
                  <p>{reviewedResult.matches[0]?.text || getDefaultOtherReason()}</p>
                  {reviewedResult.matches[0]?.reason ? <small>{reviewedResult.matches[0].reason}</small> : null}
                </div>
              ) : (
                <>
                  {!!reviewedResult.matches.length && (
                    <div className="match-list">
                      {reviewedResult.matches.map((item) => {
                        const reasonPresentation = getReasonHighlightPresentationState(
                          activeReasonHighlight,
                          item,
                          sourceSentences,
                        );

                        return (
                          <div className="match-item" key={item.entry_id}>
                            <div className="match-item__top">
                              <ResultTag code={item.type_code} />
                              <span>{item.category}</span>
                            </div>
                            <p>{item.text}</p>
                            {item.reason ? (
                              reasonPresentation.isClickable ? (
                                <button
                                  aria-pressed={reasonPresentation.isActive}
                                  onClick={() =>
                                    setActiveReasonHighlight((currentHighlight) =>
                                      toggleReasonHighlight(currentHighlight, item, sourceSentences),
                                    )
                                  }
                                  className="chunk-card__reason-button"
                                  type="button"
                                >
                                  <small className="chunk-card__reason-text">{item.reason}</small>
                                </button>
                              ) : (
                                <small>{item.reason}</small>
                              )
                            ) : null}
                          </div>
                        );
                      })}
                    </div>
                  )}
                </>
              )
            ) : null}
          </div>
        </div>
      </section>

      {(mode !== "preview" || !isPreviewCollapsed) && (
        <footer className="chunk-card__result">
          <div className="chunk-card__label-row">
            {reviewedResult ? (
              compareDisplayState.state === "no-hit" ? (
                <ResultTag code="OTHER" />
              ) : (
                <span className="muted">可通过类型筛选按钮快速定位该段</span>
              )
            ) : (
              <span className="muted">智能分析后将显示类型标签</span>
            )}
            {compareDisplayState.state === "hit" ? <span className="result-hit">{resultTypeCodes.join(" / ")}</span> : null}
          </div>
        </footer>
      )}

      {typeof document !== "undefined" && reviewModal ? createPortal(reviewModal, document.body) : null}
      {typeof document !== "undefined" && addModal ? createPortal(addModal, document.body) : null}
    </article>
  );
}

export default ChunkCard;
