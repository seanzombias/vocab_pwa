import { createClient, type Client, type InValue } from "@libsql/client/web";

import type { Env, VocabItem, VocabPayload } from "./types";

const SCHEMA_SQL = `
CREATE TABLE IF NOT EXISTS vocab (
    id TEXT PRIMARY KEY,
    word TEXT NOT NULL,
    phrase TEXT NOT NULL DEFAULT '',
    meaning TEXT NOT NULL,
    sentence TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT '',
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_vocab_created_at ON vocab(created_at);
`;

let schemaReady = false;

export function normalizeTursoUrl(url: string): string {
  const trimmed = url.trim();
  if (trimmed.startsWith("libsql://")) {
    return `https://${trimmed.slice("libsql://".length)}`;
  }
  return trimmed;
}

export function createDb(env: Env): Client {
  return createClient({
    url: normalizeTursoUrl(env.TURSO_DATABASE_URL),
    authToken: env.TURSO_AUTH_TOKEN,
  });
}

export async function ensureSchema(client: Client): Promise<void> {
  if (schemaReady) {
    return;
  }
  for (const statement of SCHEMA_SQL.split(";")) {
    const sql = statement.trim();
    if (sql) {
      await client.execute(sql);
    }
  }
  schemaReady = true;
}

function utcNowIso(): string {
  return new Date().toISOString().replace(/\.\d{3}Z$/, "+00:00");
}

function rowToDict(row: Record<string, unknown>): VocabItem {
  const tagsValue = row.tags ?? "[]";
  let tags: string[] = [];
  if (typeof tagsValue === "string") {
    try {
      tags = JSON.parse(tagsValue);
    } catch {
      tags = [];
    }
  } else if (Array.isArray(tagsValue)) {
    tags = tagsValue.map(String);
  }

  return {
    id: String(row.id ?? ""),
    word: String(row.word ?? ""),
    phrase: String(row.phrase ?? ""),
    meaning: String(row.meaning ?? ""),
    sentence: String(row.sentence ?? ""),
    source: String(row.source ?? ""),
    tags,
    created_at: String(row.created_at ?? ""),
  };
}

export async function ping(client: Client): Promise<boolean> {
  const result = await client.execute("SELECT 1 AS ok");
  const row = result.rows[0] as Record<string, unknown> | undefined;
  return Number(row?.ok) === 1;
}

export async function listVocab(
  client: Client,
  options: {
    date?: string | null;
    tag?: string | null;
    today?: boolean;
    query?: string | null;
  } = {}
): Promise<VocabItem[]> {
  let sql = "SELECT * FROM vocab WHERE 1=1";
  const args: InValue[] = [];

  if (options.today) {
    const todayPrefix = new Date().toISOString().slice(0, 10);
    sql += " AND created_at LIKE ?";
    args.push(`${todayPrefix}%`);
  } else if (options.date) {
    sql += " AND created_at LIKE ?";
    args.push(`${options.date}%`);
  }

  if (options.query) {
    sql += " AND (word LIKE ? OR phrase LIKE ? OR meaning LIKE ? OR sentence LIKE ?)";
    const like = `%${options.query}%`;
    args.push(like, like, like, like);
  }

  sql += " ORDER BY created_at DESC, word ASC";
  const result = await client.execute({ sql, args });
  let rows = result.rows.map((row) => rowToDict(row as Record<string, unknown>));

  if (options.tag) {
    rows = rows.filter((item) => item.tags.includes(options.tag!));
  }

  if (options.today && rows.length === 0) {
    const dates = await getDates(client);
    const latest = dates[0];
    if (latest) {
      return listVocab(client, { ...options, today: false, date: latest });
    }
  }

  return rows;
}

export async function getTags(client: Client): Promise<Array<{ tag: string; count: number }>> {
  const result = await client.execute("SELECT tags FROM vocab");
  const counts = new Map<string, number>();
  for (const row of result.rows) {
    const item = rowToDict(row as Record<string, unknown>);
    for (const tag of item.tags) {
      counts.set(tag, (counts.get(tag) ?? 0) + 1);
    }
  }
  return [...counts.entries()]
    .map(([tag, count]) => ({ tag, count }))
    .sort((a, b) => a.tag.localeCompare(b.tag));
}

export async function getDates(client: Client): Promise<string[]> {
  const result = await client.execute("SELECT created_at FROM vocab ORDER BY created_at DESC");
  const dates = new Set<string>();
  for (const row of result.rows) {
    const createdAt = String((row as Record<string, unknown>).created_at ?? "");
    if (createdAt.length >= 10) {
      dates.add(createdAt.slice(0, 10));
    }
  }
  return [...dates].sort().reverse();
}

function normalizePayload(payload: VocabPayload): VocabItem {
  const word = String(payload.word ?? "").trim();
  const meaning = String(payload.meaning ?? "").trim();
  const sentence = String(payload.sentence ?? "").trim();
  if (!word || !meaning || !sentence) {
    throw new Error("word, meaning, and sentence are required");
  }

  let tags = payload.tags ?? [];
  if (typeof tags === "string") {
    tags = tags
      .split(",")
      .map((part) => part.trim())
      .filter(Boolean);
  }

  return {
    id: payload.id ?? crypto.randomUUID(),
    word,
    phrase: String(payload.phrase ?? "").trim(),
    meaning,
    sentence,
    source: String(payload.source ?? "").trim(),
    tags,
    created_at: payload.created_at ?? utcNowIso(),
  };
}

export async function createVocab(client: Client, payload: VocabPayload): Promise<VocabItem> {
  const entry = normalizePayload(payload);
  await client.execute({
    sql: `
      INSERT INTO vocab (id, word, phrase, meaning, sentence, source, tags, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `,
    args: [
      entry.id,
      entry.word,
      entry.phrase,
      entry.meaning,
      entry.sentence,
      entry.source,
      JSON.stringify(entry.tags),
      entry.created_at,
    ],
  });
  return entry;
}

export async function vocabExists(
  client: Client,
  source: string,
  word: string,
  sentence: string
): Promise<boolean> {
  const result = await client.execute({
    sql: `
      SELECT id FROM vocab
      WHERE lower(source) = lower(?)
        AND lower(word) = lower(?)
        AND lower(sentence) = lower(?)
      LIMIT 1
    `,
    args: [source.trim(), word.trim(), sentence.trim()],
  });
  return result.rows.length > 0;
}

export async function createMany(client: Client, payloads: VocabPayload[]): Promise<VocabItem[]> {
  const items: VocabItem[] = [];
  for (const payload of payloads) {
    items.push(await createVocab(client, payload));
  }
  return items;
}

export async function createManyDeduped(
  client: Client,
  payloads: VocabPayload[]
): Promise<{ items: VocabItem[]; count: number; skipped: number }> {
  const items: VocabItem[] = [];
  let skipped = 0;
  for (const payload of payloads) {
    const entry = normalizePayload(payload);
    if (await vocabExists(client, entry.source, entry.word, entry.sentence)) {
      skipped += 1;
      continue;
    }
    items.push(await createVocab(client, entry));
  }
  return { items, count: items.length, skipped };
}

export async function deleteVocab(client: Client, entryId: string): Promise<boolean> {
  const existing = await client.execute({
    sql: "SELECT id FROM vocab WHERE id = ?",
    args: [entryId],
  });
  if (!existing.rows.length) {
    return false;
  }
  await client.execute({
    sql: "DELETE FROM vocab WHERE id = ?",
    args: [entryId],
  });
  return true;
}

export function ankiFront(item: VocabItem): string {
  return item.phrase ? `${item.word}\n${item.phrase}` : item.word;
}

export function ankiBack(item: VocabItem): string {
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

export function csvEscape(value: string): string {
  if (/[",\n]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

export function exportAnkiCsv(items: VocabItem[]): string {
  const lines = ["Front,Back,Tags"];
  for (const item of items) {
    const tags = item.tags.join(" ");
    lines.push([ankiFront(item), ankiBack(item), tags].map(csvEscape).join(","));
  }
  return `\ufeff${lines.join("\n")}`;
}
