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
  return "https://vocab-pwa-api.onrender.com";
})();

export function asset(path) {
  return `${BASE_PATH}${path.startsWith("/") ? path : `/${path}`}`;
}
