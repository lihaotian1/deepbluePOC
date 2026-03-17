export type TypeCode = string;
export type ResultFilterType = string;

export interface Chunk {
  chunk_id: number;
  source: string;
  heading: string;
  level: number;
  line_no: number;
  content: string;
}

export interface UploadResponse {
  doc_id: string;
  source_file_name: string;
  chunks: Chunk[];
}

export interface MatchItem {
  entry_id: string;
  category: string;
  text: string;
  type_code: TypeCode;
  reason: string;
  evidence_sentence_index?: number | null;
  evidence_sentence_text?: string;
}

export interface ChunkCompareResult {
  chunk_id: number;
  heading: string;
  content: string;
  categories: string[];
  matches: MatchItem[];
  label: "命中" | "其他";
}

export interface KnowledgeBaseFileSummary {
  file_name: string;
  display_name: string;
}

export interface KnowledgeBaseItem {
  text: string;
  value: string;
}

export interface KnowledgeBaseCategory {
  name: string;
  items: KnowledgeBaseItem[];
}

export interface KnowledgeBaseDocument {
  file_name: string;
  display_name: string;
  format: "grouped" | "flat_key_value";
  categories: KnowledgeBaseCategory[];
}

export interface KnowledgeBaseCreateRequest {
  file_name: string;
  format: "grouped" | "flat_key_value";
}

export type AppPage = "home" | "knowledge-base";
