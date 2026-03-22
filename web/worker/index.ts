interface Env {
  DB: D1Database;
  ASSETS: Fetcher;
}

const COLS =
  "id, reactants, conditions, product, named_reaction, category, difficulty, transform, notes, raw_conditions, source_row";
const WHERE_VALID = "WHERE error = ''";

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    if (!url.pathname.startsWith("/api/")) {
      return env.ASSETS.fetch(request);
    }

    try {
      const response = await handleApi(url, env);
      response.headers.set("Access-Control-Allow-Origin", "*");
      return response;
    } catch (err) {
      return json({ error: String(err) }, 500);
    }
  },
} satisfies ExportedHandler<Env>;

async function handleApi(url: URL, env: Env): Promise<Response> {
  const path = url.pathname;

  if (path === "/api/reactions/count") {
    const row = await env.DB.prepare(
      `SELECT COUNT(*) as count FROM reactions ${WHERE_VALID}`
    ).first();
    return json({ count: row?.count ?? 0 });
  }

  if (path === "/api/reactions/first") {
    const row = await env.DB.prepare(
      `SELECT ${COLS} FROM reactions ${WHERE_VALID} ORDER BY id ASC LIMIT 1`
    ).first();
    if (!row) return json({ error: "no reactions" }, 404);
    return json(row);
  }

  if (path === "/api/reactions/random") {
    const row = await env.DB.prepare(
      `SELECT ${COLS} FROM reactions ${WHERE_VALID} ORDER BY RANDOM() LIMIT 1`
    ).first();
    if (!row) return json({ error: "no reactions" }, 404);
    return json(row);
  }

  // /api/reactions/:id/next
  const nextMatch = path.match(/^\/api\/reactions\/(\d+)\/next$/);
  if (nextMatch) {
    const id = Number(nextMatch[1]);
    let row = await env.DB.prepare(
      `SELECT ${COLS} FROM reactions ${WHERE_VALID} AND id > ? ORDER BY id ASC LIMIT 1`
    ).bind(id).first();
    if (!row) {
      row = await env.DB.prepare(
        `SELECT ${COLS} FROM reactions ${WHERE_VALID} ORDER BY id ASC LIMIT 1`
      ).first();
    }
    if (!row) return json({ error: "no reactions" }, 404);
    return json(row);
  }

  // /api/reactions/:id/prev
  const prevMatch = path.match(/^\/api\/reactions\/(\d+)\/prev$/);
  if (prevMatch) {
    const id = Number(prevMatch[1]);
    let row = await env.DB.prepare(
      `SELECT ${COLS} FROM reactions ${WHERE_VALID} AND id < ? ORDER BY id DESC LIMIT 1`
    ).bind(id).first();
    if (!row) {
      row = await env.DB.prepare(
        `SELECT ${COLS} FROM reactions ${WHERE_VALID} ORDER BY id DESC LIMIT 1`
      ).first();
    }
    if (!row) return json({ error: "no reactions" }, 404);
    return json(row);
  }

  // /api/reactions/:id
  const idMatch = path.match(/^\/api\/reactions\/(\d+)$/);
  if (idMatch) {
    const row = await env.DB.prepare(
      `SELECT ${COLS} FROM reactions WHERE id = ?`
    )
      .bind(Number(idMatch[1]))
      .first();
    if (!row) return json({ error: "not found" }, 404);
    return json(row);
  }

  if (path === "/api/reactions") {
    const q = url.searchParams.get("q");
    const page = Math.max(1, Number(url.searchParams.get("page") ?? 1));
    const perPage = Math.min(
      100,
      Math.max(1, Number(url.searchParams.get("per_page") ?? 24))
    );
    const offset = (page - 1) * perPage;

    let where = WHERE_VALID;
    const params: string[] = [];

    if (q) {
      where +=
        " AND (reactants LIKE ? OR product LIKE ? OR conditions LIKE ? OR named_reaction LIKE ? OR category LIKE ?)";
      for (let i = 0; i < 5; i++) params.push(`%${q}%`);
    }

    const countRow = await env.DB.prepare(
      `SELECT COUNT(*) as count FROM reactions ${where}`
    )
      .bind(...params)
      .first();
    const total = (countRow?.count as number) ?? 0;

    const { results } = await env.DB.prepare(
      `SELECT ${COLS} FROM reactions ${where} ORDER BY id LIMIT ? OFFSET ?`
    )
      .bind(...params, perPage, offset)
      .all();

    return json({
      total,
      page,
      per_page: perPage,
      pages: Math.ceil(total / perPage),
      reactions: results,
    });
  }

  return json({ error: "not found" }, 404);
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
