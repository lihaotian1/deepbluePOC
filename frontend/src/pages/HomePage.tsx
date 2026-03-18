import { useEffect, useMemo, useState } from "react";

import { exportExcel, patchChunks, saveDocumentReviewState, uploadDocument } from "../api/client";
import { streamCompare } from "../api/sse";
import ChunkCard from "../components/ChunkCard";
import ComparePanel from "../components/ComparePanel";
import UploadPanel from "../components/UploadPanel";
import {
  DEFAULT_COMPARE_KB_FILES,
  STANDARD_KB_FILE_NAME,
  buildFilterModelForKnowledgeBase,
  collectTypeCodes,
  invalidateCompareStateAfterChunkEdit,
  mergeChunkCompareResult,
  toggleKnowledgeBaseSelection,
} from "./homePageCompareState";
import { normalizeReviewResult } from "./homePageReviewState";
import type {
  Chunk,
  ChunkCompareResult,
  KnowledgeBaseFileSummary,
  ResultFilterType,
} from "../types";

interface HomePageProps {
  compareKnowledgeBases: KnowledgeBaseFileSummary[];
}

function HomePage({ compareKnowledgeBases }: HomePageProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [docId, setDocId] = useState("");
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [resultsByKb, setResultsByKb] = useState<Record<string, Record<number, ChunkCompareResult>>>({});
  const [selectedCompareKbFiles, setSelectedCompareKbFiles] = useState<string[]>([STANDARD_KB_FILE_NAME]);
  const [activeResultKbFile, setActiveResultKbFile] = useState(STANDARD_KB_FILE_NAME);
  const [logs, setLogs] = useState<string[]>([]);
  const [progressText, setProgressText] = useState("等待上传文件");
  const [activeFilter, setActiveFilter] = useState<ResultFilterType>("ALL");
  const [hasPendingChunkSync, setHasPendingChunkSync] = useState(false);
  const [hasPendingReviewSync, setHasPendingReviewSync] = useState(false);
  const [submittedForReview, setSubmittedForReview] = useState(false);

  const compareOptions = useMemo(() => {
    return DEFAULT_COMPARE_KB_FILES.map((fileName) => {
      return compareKnowledgeBases.find((item) => item.file_name === fileName) ?? {
        file_name: fileName,
        display_name: fileName.replace(/\.json$/, ""),
      };
    });
  }, [compareKnowledgeBases]);

  useEffect(() => {
    if (selectedCompareKbFiles.includes(activeResultKbFile)) {
      return;
    }

    setActiveResultKbFile(selectedCompareKbFiles[0] ?? STANDARD_KB_FILE_NAME);
  }, [activeResultKbFile, selectedCompareKbFiles]);

  const sortedChunks = useMemo(() => [...chunks].sort((a, b) => a.chunk_id - b.chunk_id), [chunks]);
  const activeResultMap = resultsByKb[activeResultKbFile] ?? {};
  const filterModel = useMemo(
    () => buildFilterModelForKnowledgeBase(activeResultKbFile, activeResultMap, sortedChunks.length),
    [activeResultKbFile, activeResultMap, sortedChunks.length],
  );

  const filteredChunks = useMemo(() => {
    if (activeFilter === "ALL") {
      return sortedChunks;
    }

    return sortedChunks.filter((chunk) => {
      const result = activeResultMap[chunk.chunk_id];
      if (!result) {
        return false;
      }

      return collectTypeCodes(result).includes(activeFilter);
    });
  }, [activeFilter, activeResultMap, sortedChunks]);

  function appendLog(line: string) {
    setLogs((prev) => [...prev, line]);
  }

  function resolveKnowledgeBaseDisplayName(fileName: string) {
    return compareOptions.find((item) => item.file_name === fileName)?.display_name ?? fileName.replace(/\.json$/, "");
  }

  function handleToggleKnowledgeBase(fileName: string) {
    setSelectedCompareKbFiles((current) =>
      toggleKnowledgeBaseSelection(
        current,
        fileName,
        compareOptions.map((item) => item.file_name),
        comparing,
      ),
    );
  }

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }
    setUploading(true);
    setProgressText("正在切分文档...");
    setLogs([]);
    setResultsByKb({});
    try {
      const response = await uploadDocument(selectedFile);
      setDocId(response.doc_id);
      setChunks(response.chunks);
      setHasPendingChunkSync(false);
      setHasPendingReviewSync(false);
      setSubmittedForReview(false);
      setActiveFilter("ALL");
      setActiveResultKbFile(selectedCompareKbFiles[0] ?? STANDARD_KB_FILE_NAME);
      setProgressText(`切分完成，共 ${response.chunks.length} 段`);
      appendLog(`上传完成: ${response.source_file_name}`);
    } catch (error) {
      setProgressText("上传失败，请检查后重试");
      appendLog(`上传失败: ${String(error)}`);
    } finally {
      setUploading(false);
    }
  }

  function handleChunkChange(chunkId: number, value: string) {
    setChunks((prev) => prev.map((chunk) => (chunk.chunk_id === chunkId ? { ...chunk, content: value } : chunk)));
    setHasPendingChunkSync(true);
    setHasPendingReviewSync(false);
    setSubmittedForReview(false);

    const nextCompareState = invalidateCompareStateAfterChunkEdit({ resultsByKb, activeFilter });
    if (nextCompareState.resultsByKb !== resultsByKb) {
      setResultsByKb(nextCompareState.resultsByKb);
    }
    if (nextCompareState.activeFilter !== activeFilter) {
      setActiveFilter(nextCompareState.activeFilter);
    }

    setProgressText("章节内容已修改，历史比对结果已失效");
  }

  function handleReviewResultChange(chunkId: number, nextResult: ChunkCompareResult) {
    setResultsByKb((prev) => ({
      ...prev,
      [activeResultKbFile]: {
        ...(prev[activeResultKbFile] ?? {}),
        [chunkId]: normalizeReviewResult(nextResult),
      },
    }));
    setHasPendingReviewSync(true);
    setSubmittedForReview(false);
  }

  function buildReviewPayload(nextSubmittedForReview: boolean) {
    return {
      compare_results_by_kb: Object.fromEntries(
        Object.entries(resultsByKb).map(([kbFile, resultMap]) => [
          kbFile,
          Object.values(resultMap)
            .map((result) => normalizeReviewResult(result))
            .sort((left, right) => left.chunk_id - right.chunk_id),
        ]),
      ),
      submitted_for_review: nextSubmittedForReview,
    };
  }

  function mapReviewResultsByKb(nextResultsByKb: Record<string, ChunkCompareResult[]>) {
    return Object.fromEntries(
      Object.entries(nextResultsByKb).map(([kbFile, resultList]) => [
        kbFile,
        Object.fromEntries(resultList.map((result) => [result.chunk_id, normalizeReviewResult(result)])),
      ]),
    );
  }

  async function syncReviewState(nextSubmittedForReview: boolean) {
    if (!docId) {
      return;
    }

    const response = await saveDocumentReviewState(docId, buildReviewPayload(nextSubmittedForReview));
    setResultsByKb(mapReviewResultsByKb(response.compare_results_by_kb));
    setSubmittedForReview(response.submitted_for_review);
    setHasPendingReviewSync(false);
  }

  async function handleCompare() {
    if (!docId || chunks.length === 0 || selectedCompareKbFiles.length === 0) {
      return;
    }
    setComparing(true);
    setActiveResultKbFile(selectedCompareKbFiles[0] ?? STANDARD_KB_FILE_NAME);
    setActiveFilter("ALL");
    setLogs([]);
    setSubmittedForReview(false);
    setHasPendingReviewSync(false);
    setProgressText("正在提交编辑内容...");

    try {
      await patchChunks(docId, chunks);
      setHasPendingChunkSync(false);
      appendLog("编辑内容已保存，开始流式比对...");
      await streamCompare(
        docId,
        selectedCompareKbFiles,
        (eventName, payload) => {
          const eventPayload = (payload || {}) as Record<string, unknown>;
          const kbFile = String(eventPayload.kb_file || "");
          const kbDisplayName = String(eventPayload.kb_display_name || resolveKnowledgeBaseDisplayName(kbFile));
          const logPrefix = kbDisplayName ? `[${kbDisplayName}] ` : "";

          if (eventName === "chunk_start") {
            const index = Number(eventPayload.index || 0);
            const total = Number(eventPayload.total || 0);
            const heading = String(eventPayload.heading || "");
            setProgressText(`${kbDisplayName} 比对进行中: ${index}/${total}`);
            appendLog(`${logPrefix}开始处理第 ${index}/${total} 段: ${heading}`);
            return;
          }

          if (eventName === "chunk_result") {
            const result = eventPayload.result as ChunkCompareResult;
            if (!result || typeof result.chunk_id !== "number" || !kbFile) {
              return;
            }
            setResultsByKb((prev) => mergeChunkCompareResult(prev, kbFile, result));
            appendLog(`${logPrefix}第 ${result.chunk_id} 段处理完成 (${result.label})`);
            return;
          }

          if (eventName === "classification") {
            const chunkId = Number(eventPayload.chunk_id || 0);
            const categories = Array.isArray(eventPayload.categories)
              ? (eventPayload.categories as string[])
              : [];
            appendLog(`${logPrefix}第 ${chunkId} 段分类: ${categories.length ? categories.join(" / ") : "其他"}`);
            return;
          }

          if (eventName === "category_match") {
            const category = String(eventPayload.category || "未知分类");
            const hitCount = Number(eventPayload.hit_count || 0);
            appendLog(`${logPrefix}分类 ${category} 命中 ${hitCount} 条`);
            return;
          }

          if (eventName === "error") {
            appendLog(`${logPrefix}处理异常: ${String(eventPayload.message || "未知错误")}`);
            return;
          }

          if (eventName === "compare_done") {
            setProgressText(`比对完成，共处理 ${selectedCompareKbFiles.length} 个知识库`);
            appendLog("全部章节比对完成");
          }
        },
        (message) => {
          appendLog(message);
        },
        {
          onRetry: (message) => {
            appendLog(message);
          },
        },
      );
    } catch (error) {
      setProgressText("比对失败，请稍后重试");
      appendLog(`比对失败: ${String(error)}`);
    } finally {
      setComparing(false);
    }
  }

  async function handleExport() {
    if (!docId) {
      return;
    }
    try {
      if (hasPendingChunkSync) {
        setProgressText("正在保存编辑内容...");
        await patchChunks(docId, chunks);
        setHasPendingChunkSync(false);
        appendLog("编辑内容已保存，历史比对结果已清除");
      }

      if (hasPendingReviewSync) {
        setProgressText("正在同步审核内容...");
        await syncReviewState(submittedForReview);
        appendLog("审核内容已同步");
      }

      setProgressText("正在导出 Excel...");
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
      appendLog("Excel 导出成功");
    } catch (error) {
      appendLog(`导出失败: ${String(error)}`);
    }
  }

  async function handleSubmitReview() {
    if (!docId) {
      return;
    }

    try {
      if (hasPendingChunkSync) {
        setProgressText("正在保存编辑内容...");
        await patchChunks(docId, chunks);
        setHasPendingChunkSync(false);
        appendLog("编辑内容已保存，审核提交将使用最新正文");
      }

      setProgressText("正在提交审核...");
      await syncReviewState(true);
      setProgressText("文档已提交审核");
      appendLog("文档已提交审核");
    } catch (error) {
      appendLog(`提交审核失败: ${String(error)}`);
    }
  }

  return (
    <section className="page-shell">
      <div className="bg-orb bg-orb--left" />
      <div className="bg-orb bg-orb--right" />

      <section className="hero">
        <p className="hero__eyebrow">AI Assistant</p>
        <h1>技术协议偏差分析POC</h1>
      </section>

      <UploadPanel
        loading={uploading}
        fileName={selectedFile?.name || ""}
        onSelectFile={setSelectedFile}
        onSubmit={handleUpload}
      />

      <ComparePanel
        hasDocument={Boolean(docId)}
        comparing={comparing}
        progressText={progressText}
        logs={logs}
        knowledgeBaseOptions={compareOptions}
        selectedKnowledgeBaseFiles={selectedCompareKbFiles}
        submittedForReview={submittedForReview}
        onToggleKnowledgeBase={handleToggleKnowledgeBase}
        onCompare={handleCompare}
        onExport={handleExport}
        onSubmitReview={handleSubmitReview}
      />

      <section className="glass-card filter-panel">
        <div className="filter-panel__head">
          <div>
            <h3>类型筛选</h3>
            {selectedCompareKbFiles.length > 1 ? <p>当前展示 {resolveKnowledgeBaseDisplayName(activeResultKbFile)} 的比对结果</p> : null}
          </div>

          {selectedCompareKbFiles.length > 1 ? (
            <div className="filter-panel__views">
              {selectedCompareKbFiles.map((fileName) => (
                <button
                  key={fileName}
                  type="button"
                  className={`btn btn-lite filter-btn ${activeResultKbFile === fileName ? "is-active" : ""}`}
                  onClick={() => {
                    setActiveResultKbFile(fileName);
                    setActiveFilter("ALL");
                  }}
                >
                  {resolveKnowledgeBaseDisplayName(fileName)}
                </button>
              ))}
            </div>
          ) : null}
        </div>

        <div className="filter-panel__buttons">
          {filterModel.order.map((filterKey) => (
            <button
              key={filterKey}
              type="button"
              className={`btn btn-lite filter-btn ${activeFilter === filterKey ? "is-active" : ""}`}
              onClick={() => setActiveFilter(filterKey)}
            >
              {filterModel.labels[filterKey]}({filterModel.counts[filterKey] ?? 0})
            </button>
          ))}
        </div>
      </section>

      <section className="chunks-grid">
        {filteredChunks.map((chunk) => (
          <ChunkCard
            key={chunk.chunk_id}
            chunk={chunk}
            result={activeResultMap[chunk.chunk_id]}
            activeKnowledgeBaseFile={activeResultKbFile}
            onChange={handleChunkChange}
            onReviewChange={handleReviewResultChange}
          />
        ))}
      </section>
    </section>
  );
}

export default HomePage;
