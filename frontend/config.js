export const BASE_PATH = (() => {
  const path = window.location.pathname;
  if (path.startsWith("/vocab_pwa")) {
    return "/vocab_pwa";
  }
  return "";
})();

export const API_BASE = (() => {
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return "http://localhost:8765";
  }
  // Cloudflare Worker（部署后 wrangler 会显示实际 URL）
  return "https://vocab-pwa-api.756121162.workers.dev";
})();

/** 读写均走 Worker + Turso，静态 JSON 仅在 API 失败时回退 */
export const USE_STATIC_DATA = false;

export function asset(path) {
  return `${BASE_PATH}${path.startsWith("/") ? path : `/${path}`}`;
}
