import { useEffect, useMemo, useRef, useState } from "react";

import { translateChunkContent } from "../api/client";
import type { Chunk, ChunkCompareResult } from "../types";
import { autosizeTextarea } from "../utils/textareaAutosize";
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

interface ChunkCardProps {
  chunk: Chunk;
  result?: ChunkCompareResult;
  onChange: (chunkId: number, value: string) => void;
}

function ChunkCard({ chunk, result, onChange }: ChunkCardProps) {
  const [mode, setMode] = useState<"preview" | "edit">("preview");
  const [expandResult, setExpandResult] = useState(false);
  const [activeReasonHighlight, setActiveReasonHighlight] = useState<{
    reasonKey: string;
    sentenceIndex: number;
  } | null>(null);
  const editorRef = useRef<HTMLTextAreaElement | null>(null);
  const collapsedTagAreaRef = useRef<HTMLDivElement | null>(null);
  const [collapsedTagAreaHeight, setCollapsedTagAreaHeight] = useState(DEFAULT_COLLAPSED_TAG_AREA_HEIGHT);
  const [translationState, setTranslationState] = useState(createChunkCardTranslationState);

  const viewState = useMemo(() => getChunkCardViewState({ expanded: expandResult }), [expandResult]);
  const title = useMemo(() => formatChunkCardTitle(chunk.heading), [chunk.heading]);
  const sourceSentences = useMemo(() => splitChunkContentIntoSentences(chunk.content), [chunk.content]);
  const reasonHighlightResetKey = useMemo(() => getReasonHighlightResetKey(chunk.content, result), [chunk.content, result]);
  const compareDisplayState = useMemo(() => normalizeChunkCompareResultDisplay(result), [result]);
  const sourceSentenceViewModels = useMemo(
    () => buildSourceSentenceViewModels(sourceSentences, activeReasonHighlight),
    [activeReasonHighlight, sourceSentences],
  );
  const resultTypeCodes = compareDisplayState.resultTypeCodes;
  const summaryTags = useMemo(() => resolveChunkSummaryTags(result), [result]);
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
  }, [mode, result?.categories, result?.label, result?.matches.length, resultTypeCodes, viewState.rightContentMode]);

  useEffect(() => {
    setActiveReasonHighlight(null);
  }, [reasonHighlightResetKey]);

  useEffect(() => {
    setTranslationState((currentState) => invalidateChunkCardTranslation(currentState, chunk.content));
  }, [chunk.content]);

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
    if (!result) {
      return (
        <div className="chunk-result-panel__summary" ref={ref}>
          <span className="chunk-summary-pill chunk-summary-pill--pending">待比对</span>
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
        <span className="chunk-summary-pill chunk-summary-pill--accent">命中 {result.matches.length} 条</span>
        {summaryTags.map((code) => (
          <ResultTag key={code} code={code} />
        ))}
      </div>
    );
  };

  return (
    <article className="glass-card chunk-card">
      <header className="chunk-card__header">
        <div>
          <h3>{title}</h3>
          <p>Level {chunk.level} · Line {chunk.line_no}</p>
        </div>
        <div className="chunk-card__switcher">
          <button
            className={`btn btn-lite ${mode === "preview" ? "is-active" : ""}`}
            onClick={() => setMode("preview")}
            type="button"
          >
            预览
          </button>
          <button
            className={`btn btn-lite ${mode === "edit" ? "is-active" : ""}`}
            onClick={() => setMode("edit")}
            type="button"
          >
            编辑
          </button>
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
            <span className="muted">知识库比对结果</span>
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
              !result ? null : compareDisplayState.state === "no-hit" ? (
                <div className="match-item">
                  <div className="match-item__top">
                    <ResultTag code="OTHER" />
                    <span>其他</span>
                  </div>
                  <p>未命中知识库条目，归类为其他。</p>
                </div>
              ) : (
                <>
                  {!!result.matches.length && (
                    <div className="match-list">
                      {result.matches.map((item) => {
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
            {result ? (
              compareDisplayState.state === "no-hit" ? (
                <ResultTag code="OTHER" />
              ) : (
                <span className="muted">可通过类型筛选按钮快速定位该段</span>
              )
            ) : (
              <span className="muted">比对后将显示类型标签</span>
            )}
            {compareDisplayState.state === "hit" ? <span className="result-hit">{resultTypeCodes.join(" / ")}</span> : null}
          </div>
        </footer>
      )}
    </article>
  );
}

export default ChunkCard;
