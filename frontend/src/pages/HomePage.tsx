import { useMemo, useState } from "react";

import { exportExcel, patchChunks, uploadDocument } from "../api/client";
import { streamCompare } from "../api/sse";
import ChunkCard from "../components/ChunkCard";
import ComparePanel from "../components/ComparePanel";
import UploadPanel from "../components/UploadPanel";
import { invalidateCompareStateAfterChunkEdit } from "./homePageCompareState";
import type { Chunk, ChunkCompareResult, ResultFilterType, TypeCode } from "../types";


const FILTER_ORDER: ResultFilterType[] = ["ALL", "P", "A", "B", "C", "OTHER"];
const FILTER_LABELS: Record<ResultFilterType, string> = {
  ALL: "ALL",
  P: "P",
  A: "A",
  B: "B",
  C: "C",
  OTHER: "其他",
};

function HomePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [comparing, setComparing] = useState(false);
  const [docId, setDocId] = useState("");
  const [chunks, setChunks] = useState<Chunk[]>([]);
  const [resultMap, setResultMap] = useState<Record<number, ChunkCompareResult>>({});
  const [logs, setLogs] = useState<string[]>([]);
  const [progressText, setProgressText] = useState("等待上传文件");
  const [activeFilter, setActiveFilter] = useState<ResultFilterType>("ALL");
  const [hasPendingChunkSync, setHasPendingChunkSync] = useState(false);

  const sortedChunks = useMemo(() => [...chunks].sort((a, b) => a.chunk_id - b.chunk_id), [chunks]);

  const filterCounts = useMemo(() => {
    const counter: Record<ResultFilterType, number> = {
      ALL: sortedChunks.length,
      P: 0,
      A: 0,
      B: 0,
      C: 0,
      OTHER: 0,
    };

    for (const chunk of sortedChunks) {
      const result = resultMap[chunk.chunk_id];
      if (!result) {
        continue;
      }
      const hitTypes = collectTypeCodes(result);
      for (const typeCode of hitTypes) {
        counter[typeCode] += 1;
      }
    }
    return counter;
  }, [resultMap, sortedChunks]);

  const filteredChunks = useMemo(() => {
    if (activeFilter === "ALL") {
      return sortedChunks;
    }

    return sortedChunks.filter((chunk) => {
      const result = resultMap[chunk.chunk_id];
      if (!result) {
        return false;
      }
      return collectTypeCodes(result).includes(activeFilter as TypeCode);
    });
  }, [activeFilter, resultMap, sortedChunks]);

  function appendLog(line: string) {
    setLogs((prev) => [...prev, line]);
  }

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }
    setUploading(true);
    setProgressText("正在切分文档...");
    setLogs([]);
    setResultMap({});
    try {
      const response = await uploadDocument(selectedFile);
      setDocId(response.doc_id);
      setChunks(response.chunks);
      setHasPendingChunkSync(false);
      setActiveFilter("ALL");
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

    const nextCompareState = invalidateCompareStateAfterChunkEdit({ resultMap, activeFilter });
    if (nextCompareState.resultMap !== resultMap) {
      setResultMap(nextCompareState.resultMap);
    }
    if (nextCompareState.activeFilter !== activeFilter) {
      setActiveFilter(nextCompareState.activeFilter);
    }

    setProgressText("章节内容已修改，历史比对结果已失效");
  }

  async function handleCompare() {
    if (!docId || chunks.length === 0) {
      return;
    }
    setComparing(true);
    setResultMap({});
    setActiveFilter("ALL");
    setLogs([]);
    setProgressText("正在提交编辑内容...");

    try {
      await patchChunks(docId, chunks);
      setHasPendingChunkSync(false);
      appendLog("编辑内容已保存，开始流式比对...");
      await streamCompare(
        docId,
        (eventName, payload) => {
          const eventPayload = (payload || {}) as Record<string, unknown>;

          if (eventName === "chunk_start") {
            const index = Number(eventPayload.index || 0);
            const total = Number(eventPayload.total || 0);
            const heading = String(eventPayload.heading || "");
            setProgressText(`比对进行中: ${index}/${total}`);
            appendLog(`开始处理第 ${index}/${total} 段: ${heading}`);
            return;
          }

          if (eventName === "chunk_result") {
            const result = eventPayload.result as ChunkCompareResult;
            if (!result || typeof result.chunk_id !== "number") {
              return;
            }
            setResultMap((prev) => ({ ...prev, [result.chunk_id]: result }));
            appendLog(`第 ${result.chunk_id} 段处理完成 (${result.label})`);
            return;
          }

          if (eventName === "classification") {
            const chunkId = Number(eventPayload.chunk_id || 0);
            const categories = Array.isArray(eventPayload.categories)
              ? (eventPayload.categories as string[])
              : [];
            appendLog(`第 ${chunkId} 段分类: ${categories.length ? categories.join(" / ") : "其他"}`);
            return;
          }

          if (eventName === "category_match") {
            const category = String(eventPayload.category || "未知分类");
            const hitCount = Number(eventPayload.hit_count || 0);
            appendLog(`分类 ${category} 命中 ${hitCount} 条`);
            return;
          }

          if (eventName === "error") {
            appendLog(`处理异常: ${String(eventPayload.message || "未知错误")}`);
            return;
          }

          if (eventName === "compare_done") {
            const done = Number(eventPayload.done || 0);
            const total = Number(eventPayload.total || 0);
            setProgressText(`比对完成: ${done}/${total}`);
            appendLog("全部章节比对完成");
          }
        },
        (message) => {
          appendLog(message);
        }
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

  return (
    <section className="page-shell">
      <div className="bg-orb bg-orb--left" />
      <div className="bg-orb bg-orb--right" />

      <section className="hero">
        <p className="hero__eyebrow">AI Assistant</p>
        <h1>智能比对</h1>
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
        onCompare={handleCompare}
        onExport={handleExport}
      />

      <section className="glass-card filter-panel">
        <div className="filter-panel__head">
          <h3>类型筛选</h3>
        </div>
        <div className="filter-panel__buttons">
          {FILTER_ORDER.map((filterKey) => (
            <button
              key={filterKey}
              type="button"
              className={`btn btn-lite filter-btn ${activeFilter === filterKey ? "is-active" : ""}`}
              onClick={() => setActiveFilter(filterKey)}
            >
              {FILTER_LABELS[filterKey]}({filterCounts[filterKey]})
            </button>
          ))}
        </div>
      </section>

      <section className="chunks-grid">
        {filteredChunks.map((chunk) => (
          <ChunkCard key={chunk.chunk_id} chunk={chunk} result={resultMap[chunk.chunk_id]} onChange={handleChunkChange} />
        ))}
      </section>
    </section>
  );
}


function collectTypeCodes(result: ChunkCompareResult): TypeCode[] {
  if (result.label === "其他" || result.matches.length === 0) {
    return ["OTHER"];
  }
  return Array.from(new Set(result.matches.map((item) => item.type_code)));
}

export default HomePage;
