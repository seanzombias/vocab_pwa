import { API_BASE, BASE_PATH, asset } from "./config.js";

const TOKEN_KEY = "vocab_pwa_api_token";
const statusText = document.getElementById("statusText");
const exportBtn = document.getElementById("exportBtn");
const tabs = document.querySelectorAll(".tab");
const panels = {
  today: document.getElementById("panel-today"),
  browse: document.getElementById("panel-browse"),
  add: document.getElementById("panel-add"),
};
const todayList = document.getElementById("todayList");
const browseList = document.getElementById("browseList");
const searchInput = document.getElementById("searchInput");
const dateFilter = document.getElementById("dateFilter");
const tagFilter = document.getElementById("tagFilter");
const addForm = document.getElementById("addForm");
const formMessage = document.getElementById("formMessage");
const cardTemplate = document.getElementById("cardTemplate");

function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

function setToken(value) {
  localStorage.setItem(TOKEN_KEY, value.trim());
}

function setStatus(text) {
  statusText.textContent = text;
}

function setFormMessage(text, isError = false) {
  formMessage.textContent = text;
  formMessage.classList.toggle("error", isError);
}

function buildQuery(params) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) {
      query.set(key, value);
    }
  });
  return query.toString();
}

async function apiGet(path, params = {}) {
  const query = buildQuery(params);
  const url = `${API_BASE}${path}${query ? `?${query}` : ""}`;
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`请求失败: ${response.status}`);
  }
  return response.json();
}

async function apiWrite(path, body) {
  const token = getToken();
  if (!token) {
    throw new Error("请先在「添加」页填写 API Token");
  }
  const response = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.error || `请求失败: ${response.status}`);
  }
  return data;
}

function formatCardText(item) {
  const lines = [`${item.word}`];
  if (item.phrase) {
    lines.push(`短语: ${item.phrase}`);
  }
  lines.push(`释义: ${item.meaning}`);
  lines.push(`原句: ${item.sentence}`);
  if (item.source) {
    lines.push(`来源: ${item.source}`);
  }
  return lines.join("\n");
}

function renderCard(item) {
  const node = cardTemplate.content.cloneNode(true);
  const card = node.querySelector(".vocab-card");
  card.querySelector(".word").textContent = item.word;
  card.querySelector(".date").textContent = (item.created_at || "").slice(0, 10);

  const phraseEl = card.querySelector(".phrase");
  if (item.phrase) {
    phraseEl.textContent = item.phrase;
  } else {
    phraseEl.remove();
  }

  card.querySelector(".meaning").textContent = item.meaning;
  card.querySelector(".sentence").textContent = item.sentence;

  const sourceEl = card.querySelector(".source");
  if (item.source) {
    sourceEl.textContent = `来源: ${item.source}`;
  } else {
    sourceEl.remove();
  }

  const tagsEl = card.querySelector(".tags");
  (item.tags || []).forEach((tag) => {
    const span = document.createElement("span");
    span.className = "tag";
    span.textContent = tag;
    tagsEl.appendChild(span);
  });

  card.querySelector(".copy-btn").addEventListener("click", async () => {
    await navigator.clipboard.writeText(formatCardText(item));
    setStatus("已复制到剪贴板");
  });

  card.querySelector(".speak-btn").addEventListener("click", () => {
    const utterance = new SpeechSynthesisUtterance(`${item.word}. ${item.sentence}`);
    utterance.lang = "en-US";
    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
  });

  return card;
}

function renderList(container, items) {
  container.innerHTML = "";
  if (!items.length) {
    container.innerHTML = '<p class="empty-state">暂无词汇</p>';
    return;
  }
  items.forEach((item) => container.appendChild(renderCard(item)));
}

async function loadToday() {
  const data = await apiGet("/api/vocab", { today: "1" });
  renderList(todayList, data.items || []);
  setStatus(`今日 ${data.count || 0} 条`);
}

async function loadBrowse() {
  const params = {
    q: searchInput.value.trim(),
    date: dateFilter.value,
    tag: tagFilter.value,
  };
  const data = await apiGet("/api/vocab", params);
  renderList(browseList, data.items || []);
  setStatus(`共 ${data.count || 0} 条`);
}

async function loadFilters() {
  const [datesData, tagsData] = await Promise.all([
    apiGet("/api/vocab/dates"),
    apiGet("/api/vocab/tags"),
  ]);

  dateFilter.innerHTML = '<option value="">全部日期</option>';
  (datesData.dates || []).forEach((date) => {
    const option = document.createElement("option");
    option.value = date;
    option.textContent = date;
    dateFilter.appendChild(option);
  });

  tagFilter.innerHTML = '<option value="">全部标签</option>';
  (tagsData.tags || []).forEach(({ tag, count }) => {
    const option = document.createElement("option");
    option.value = tag;
    option.textContent = `${tag} (${count})`;
    tagFilter.appendChild(option);
  });
}

function switchTab(name) {
  tabs.forEach((tab) => tab.classList.toggle("active", tab.dataset.tab === name));
  Object.entries(panels).forEach(([key, panel]) => {
    panel.classList.toggle("active", key === name);
  });
  if (name === "today") {
    loadToday().catch(handleError);
  }
  if (name === "browse") {
    Promise.all([loadFilters(), loadBrowse()]).catch(handleError);
  }
}

function handleError(error) {
  setStatus(error.message || "加载失败");
}

function currentExportQuery() {
  const activeTab = document.querySelector(".tab.active")?.dataset.tab;
  if (activeTab === "today") {
    return buildQuery({ today: "1" });
  }
  return buildQuery({
    q: searchInput.value.trim(),
    date: dateFilter.value,
    tag: tagFilter.value,
  });
}

tabs.forEach((tab) => {
  tab.addEventListener("click", () => switchTab(tab.dataset.tab));
});

[searchInput, dateFilter, tagFilter].forEach((el) => {
  el.addEventListener("change", () => loadBrowse().catch(handleError));
  el.addEventListener("input", () => loadBrowse().catch(handleError));
});

exportBtn.addEventListener("click", () => {
  const query = currentExportQuery();
  window.open(`${API_BASE}/api/export/anki.csv${query ? `?${query}` : ""}`, "_blank");
});

addForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const formData = new FormData(addForm);
  const token = String(formData.get("token") || "").trim();
  if (token) {
    setToken(token);
  }

  const tags = String(formData.get("tags") || "")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean);

  try {
    await apiWrite("/api/vocab", {
      word: formData.get("word"),
      phrase: formData.get("phrase"),
      meaning: formData.get("meaning"),
      sentence: formData.get("sentence"),
      source: formData.get("source"),
      tags,
    });
    setFormMessage("保存成功");
    addForm.reset();
    const savedToken = getToken();
    addForm.token.value = savedToken;
    await loadToday();
  } catch (error) {
    setFormMessage(error.message || "保存失败", true);
  }
});

if ("serviceWorker" in navigator) {
  navigator.serviceWorker.register(`${BASE_PATH}/sw.js`).catch(() => {});
}

const savedToken = getToken();
if (savedToken) {
  addForm.token.value = savedToken;
}

loadToday().catch(handleError);
