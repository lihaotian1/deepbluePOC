const DEFAULT_API_BASE = "/api/v1";

export function normalizeApiBase(apiBase?: string | null): string {
  const trimmed = apiBase?.trim();
  if (!trimmed) {
    return DEFAULT_API_BASE;
  }

  return trimmed.replace(/\/+$/, "");
}

export function resolveServerBase(apiBase: string): string {
  return normalizeApiBase(apiBase).replace(/\/api\/v1$/, "");
}

export function buildAssetUrl(apiBase: string, path: string): string {
  return `${resolveServerBase(apiBase)}${path}`;
}
