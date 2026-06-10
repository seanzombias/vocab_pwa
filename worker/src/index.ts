import { Hono } from "hono";
import { cors } from "hono/cors";

import {
  createDb,
  createManyDeduped,
  createVocab,
  deleteVocab,
  ensureSchema,
  exportAnkiCsv,
  getDates,
  getTags,
  listVocab,
  ping,
} from "./db";
import type { Env, VocabPayload } from "./types";

const app = new Hono<{ Bindings: Env }>();

app.use("*", async (c, next) => {
  const origins = c.env.ALLOWED_ORIGINS.split(",").map((origin) => origin.trim()).filter(Boolean);
  return cors({
    origin: (origin) => (origin && origins.includes(origin) ? origin : origins[0] ?? "*"),
    allowMethods: ["GET", "POST", "DELETE", "OPTIONS"],
    allowHeaders: ["Content-Type", "Authorization"],
  })(c, next);
});

function requireToken(c: { req: { header: (name: string) => string | undefined }; env: Env }) {
  const auth = c.req.header("Authorization") ?? "";
  const token = auth.startsWith("Bearer ") ? auth.slice(7).trim() : "";
  if (!token || token !== c.env.VOCAB_API_TOKEN) {
    return false;
  }
  return true;
}

async function withDb(c: { env: Env }, handler: (client: ReturnType<typeof createDb>) => Promise<Response>) {
  try {
    const client = createDb(c.env);
    await ensureSchema(client);
    return await handler(client);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return Response.json({ status: "error", error: message }, { status: 503 });
  }
}

app.get("/", (c) =>
  Response.json({
    service: "vocab-pwa-api",
    status: "ok",
    endpoints: [
      "GET /api/health",
      "GET /api/vocab",
      "GET /api/vocab/dates",
      "GET /api/vocab/tags",
      "GET /api/export/anki.csv",
      "POST /api/vocab",
      "POST /api/vocab/import",
      "DELETE /api/vocab/:entryId",
    ],
  })
);

app.get("/api/health", (c) =>
  withDb(c, async (client) => {
    const ok = await ping(client);
    return Response.json({ status: "ok", db: "turso", db_ok: ok });
  })
);

app.get("/api/vocab", (c) =>
  withDb(c, async (client) => {
    const today = ["1", "true", "yes"].includes(c.req.query("today") ?? "");
    const items = await listVocab(client, {
      date: c.req.query("date") ?? null,
      tag: c.req.query("tag") ?? null,
      today,
      query: c.req.query("q") ?? null,
    });
    return Response.json({ items, count: items.length });
  })
);

app.get("/api/vocab/tags", (c) =>
  withDb(c, async (client) => {
    const tags = await getTags(client);
    return Response.json({ tags });
  })
);

app.get("/api/vocab/dates", (c) =>
  withDb(c, async (client) => {
    const dates = await getDates(client);
    return Response.json({ dates });
  })
);

app.post("/api/vocab", async (c) => {
  if (!requireToken(c)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const payload = (await c.req.json().catch(() => ({}))) as VocabPayload;
  return withDb(c, async (client) => {
    try {
      const item = await createVocab(client, payload);
      return Response.json({ item }, { status: 201 });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return Response.json({ error: message }, { status: 400 });
    }
  });
});

app.post("/api/vocab/import", async (c) => {
  if (!requireToken(c)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const payload = await c.req.json().catch(() => null);
  if (!Array.isArray(payload)) {
    return Response.json({ error: "Expected a JSON array" }, { status: 400 });
  }
  return withDb(c, async (client) => {
    try {
      const result = await createManyDeduped(client, payload as VocabPayload[]);
      return Response.json(result, { status: 201 });
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      return Response.json({ error: message }, { status: 400 });
    }
  });
});

app.delete("/api/vocab/:entryId", async (c) => {
  if (!requireToken(c)) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const entryId = c.req.param("entryId");
  return withDb(c, async (client) => {
    const ok = await deleteVocab(client, entryId);
    if (!ok) {
      return Response.json({ error: "Not found" }, { status: 404 });
    }
    return Response.json({ ok: true });
  });
});

app.get("/api/export/anki.csv", (c) =>
  withDb(c, async (client) => {
    const today = ["1", "true", "yes"].includes(c.req.query("today") ?? "");
    const items = await listVocab(client, {
      date: c.req.query("date") ?? null,
      tag: c.req.query("tag") ?? null,
      today,
      query: c.req.query("q") ?? null,
    });
    const csv = exportAnkiCsv(items);
    return new Response(csv, {
      headers: {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="vocab_anki.csv"',
      },
    });
  })
);

export default app;
