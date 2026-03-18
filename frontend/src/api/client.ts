import axios from "axios";

import type {
  Chunk,
  DocumentReviewResponse,
  DocumentReviewUpdateRequest,
  KnowledgeBaseCreateRequest,
  KnowledgeBaseDocument,
  KnowledgeBaseFileSummary,
  TranslationResponse,
  UploadResponse,
} from "../types";
import { buildAssetUrl, normalizeApiBase, resolveServerBase } from "./url";

const apiBase = normalizeApiBase(import.meta.env.VITE_API_BASE_URL);

export const http = axios.create({
  baseURL: apiBase,
  timeout: 120000,
});

export async function uploadDocument(file: File): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const response = await http.post<UploadResponse>("/documents/upload", form, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
}

export async function patchChunks(docId: string, chunks: Chunk[]): Promise<UploadResponse> {
  const response = await http.patch<UploadResponse>(`/documents/${docId}/chunks`, {
    chunks: chunks.map((chunk) => ({
      chunk_id: chunk.chunk_id,
      content: chunk.content,
    })),
  });
  return response.data;
}

export async function saveDocumentReviewState(
  docId: string,
  payload: DocumentReviewUpdateRequest,
): Promise<DocumentReviewResponse> {
  const response = await http.put<DocumentReviewResponse>(`/documents/${docId}/review`, payload);
  return response.data;
}

export async function exportExcel(docId: string): Promise<Blob> {
  const response = await http.get(`/documents/${docId}/export.xlsx`, {
    responseType: "blob",
  });
  return response.data;
}

export async function translateChunkContent(text: string): Promise<TranslationResponse> {
  const response = await http.post<TranslationResponse>("/translate/chinese", {
    text,
  });
  return response.data;
}

export async function listKnowledgeBases(): Promise<KnowledgeBaseFileSummary[]> {
  const response = await http.get<KnowledgeBaseFileSummary[]>("/knowledge-bases");
  return response.data;
}

export async function getKnowledgeBaseDocument(fileName: string): Promise<KnowledgeBaseDocument> {
  const response = await http.get<KnowledgeBaseDocument>(`/knowledge-bases/${encodeURIComponent(fileName)}`);
  return response.data;
}

export async function saveKnowledgeBaseDocument(
  fileName: string,
  document: KnowledgeBaseDocument
): Promise<KnowledgeBaseDocument> {
  const response = await http.put<KnowledgeBaseDocument>(`/knowledge-bases/${encodeURIComponent(fileName)}`, document);
  return response.data;
}

export async function createKnowledgeBaseDocument(
  payload: KnowledgeBaseCreateRequest
): Promise<KnowledgeBaseDocument> {
  const response = await http.post<KnowledgeBaseDocument>("/knowledge-bases", payload);
  return response.data;
}

export async function deleteKnowledgeBaseDocument(fileName: string): Promise<void> {
  await http.delete(`/knowledge-bases/${encodeURIComponent(fileName)}`);
}

export function getApiBase() {
  return apiBase;
}

export function getServerBase() {
  return resolveServerBase(apiBase);
}

export function getAssetUrl(path: string) {
  return buildAssetUrl(apiBase, path);
}
