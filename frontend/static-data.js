import { asset } from "./config.js";

const LOCAL_KEY = "vocab_pwa_local_entries";
let cachedItems = null;

function readLocalEntries() {
  try {
    const raw = localStorage.getItem(LOCAL_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeLocalEntries(items) {
  localStorage.setItem(LOCAL_KEY, JSON.stringify(items));
}

export async function loadAllItems() {
  if (cachedItems) {
    return cachedItems;
  }
  const response = await fetch(asset("/data/vocab.json"));
  if (!response.ok) {
    throw new Error("无法加载词汇数据");
  }
  const staticItems = await response.json();
  cachedItems = [...staticItems, ...readLocalEntries()];
  return cachedItems;
}

export function addLocalEntry(entry) {
  const items = readLocalEntries();
  items.unshift(entry);
  writeLocalEntries(items);
  cachedItems = null;
}

function todayPrefix() {
  return new Date().toISOString().slice(0, 10);
}

function filterItems(items, { today = false, date = "", tag = "", query = "" } = {}) {
  let result = items;

  if (today) {
    const prefix = todayPrefix();
    result = result.filter((item) => (item.created_at || "").startsWith(prefix));
    if (!result.length) {
      const allDates = [...new Set(items.map((item) => (item.created_at || "").slice(0, 10)))].sort().reverse();
      const latest = allDates[0];
      if (latest) {
        result = items.filter((item) => (item.created_at || "").startsWith(latest));
      }
    }
  } else if (date) {
    result = result.filter((item) => (item.created_at || "").startsWith(date));
  }

  if (query) {
    const needle = query.toLowerCase();
    result = result.filter((item) =>
      [item.word, item.phrase, item.meaning, item.sentence].some((part) =>
        String(part || "").toLowerCase().includes(needle)
      )
    );
  }

  if (tag) {
    result = result.filter((item) => (item.tags || []).includes(tag));
  }

  return [...result].sort((a, b) => {
    const dateCmp = (b.created_at || "").localeCompare(a.created_at || "");
    return dateCmp !== 0 ? dateCmp : (a.word || "").localeCompare(b.word || "");
  });
}

export async function staticListVocab(params = {}) {
  const items = await loadAllItems();
  const filtered = filterItems(items, params);
  return { items: filtered, count: filtered.length };
}

export async function staticGetTags() {
  const items = await loadAllItems();
  const counts = {};
  items.forEach((item) => {
    (item.tags || []).forEach((tag) => {
      counts[tag] = (counts[tag] || 0) + 1;
    });
  });
  return {
    tags: Object.entries(counts)
      .map(([tag, count]) => ({ tag, count }))
      .sort((a, b) => a.tag.localeCompare(b.tag)),
  };
}

export async function staticGetDates() {
  const items = await loadAllItems();
  const dates = new Set();
  items.forEach((item) => {
    const created = item.created_at || "";
    if (created.length >= 10) {
      dates.add(created.slice(0, 10));
    }
  });
  return { dates: [...dates].sort().reverse() };
}

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function ankiFront(item) {
  const phrase = item.phrase || "";
  return phrase ? `${item.word}\n${phrase}` : item.word;
}

function ankiBack(item) {
  const parts = [item.meaning];
  if (item.phrase) {
    parts.push(`短语: ${item.phrase}`);
  }
  parts.push(`原句: ${item.sentence}`);
  if (item.source) {
    parts.push(`来源: ${item.source}`);
  }
  return parts.join("\n\n");
}

export async function staticExportAnkiCsv(params = {}) {
  const { items } = await staticListVocab(params);
  const lines = ["Front,Back,Tags"];
  items.forEach((item) => {
    const tags = (item.tags || []).join(" ");
    lines.push([ankiFront(item), ankiBack(item), tags].map(csvEscape).join(","));
  });
  return "\ufeff" + lines.join("\n");
}

export function createLocalEntry(payload) {
  const word = String(payload.word || "").trim();
  const meaning = String(payload.meaning || "").trim();
  const sentence = String(payload.sentence || "").trim();
  if (!word || !meaning || !sentence) {
    throw new Error("word, meaning, and sentence are required");
  }

  let tags = payload.tags || [];
  if (typeof tags === "string") {
    tags = tags
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
  }

  return {
    id: crypto.randomUUID(),
    word,
    phrase: String(payload.phrase || "").trim(),
    meaning,
    sentence,
    source: String(payload.source || "").trim(),
    tags,
    created_at: new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00"),
  };
}

export function todayStatusMessage(count, items, allItems) {
  const prefix = todayPrefix();
  const todayCount = allItems.filter((item) => (item.created_at || "").startsWith(prefix)).length;
  if (todayCount > 0) {
    return `今日 ${todayCount} 条`;
  }
  const latest = (items[0]?.created_at || "").slice(0, 10);
  return latest ? `今日暂无新词，显示 ${latest} 共 ${count} 条` : `共 ${count} 条`;
}
