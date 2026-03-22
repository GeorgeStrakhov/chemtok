import sqlite3
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "reactions_augmented_combined.db"

COLS = "id, reactants, conditions, product, named_reaction, category, difficulty, transform, notes, raw_conditions, source_row"
WHERE_VALID = "WHERE error = ''"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/api/reactions")
def list_reactions(
    q: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
):
    conn = get_db()
    offset = (page - 1) * per_page
    where_clauses = ["error = ''"]
    params: list = []

    if q:
        where_clauses.append("(reactants LIKE ? OR product LIKE ? OR conditions LIKE ? OR named_reaction LIKE ? OR category LIKE ?)")
        params.extend([f"%{q}%"] * 5)

    where = f"WHERE {' AND '.join(where_clauses)}"

    count = conn.execute(f"SELECT COUNT(*) FROM reactions {where}", params).fetchone()[0]
    rows = conn.execute(
        f"SELECT {COLS} FROM reactions {where} ORDER BY id LIMIT ? OFFSET ?",
        [*params, per_page, offset],
    ).fetchall()
    conn.close()

    return {
        "total": count,
        "page": page,
        "per_page": per_page,
        "pages": (count + per_page - 1) // per_page,
        "reactions": [dict(r) for r in rows],
    }


@app.get("/api/reactions/count")
def reaction_count():
    conn = get_db()
    count = conn.execute(f"SELECT COUNT(*) FROM reactions {WHERE_VALID}").fetchone()[0]
    conn.close()
    return {"count": count}


@app.get("/api/reactions/first")
def first_reaction():
    conn = get_db()
    row = conn.execute(
        f"SELECT {COLS} FROM reactions {WHERE_VALID} ORDER BY id ASC LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row)


@app.get("/api/reactions/random")
def random_reaction():
    conn = get_db()
    row = conn.execute(
        f"SELECT {COLS} FROM reactions {WHERE_VALID} ORDER BY RANDOM() LIMIT 1"
    ).fetchone()
    conn.close()
    return dict(row)


@app.get("/api/reactions/{reaction_id}")
def get_reaction(reaction_id: int):
    conn = get_db()
    row = conn.execute(
        f"SELECT {COLS} FROM reactions WHERE id = ?",
        [reaction_id],
    ).fetchone()
    conn.close()
    if not row:
        return {"error": "not found"}
    return dict(row)


@app.get("/api/reactions/{reaction_id}/next")
def next_reaction(reaction_id: int):
    conn = get_db()
    row = conn.execute(
        f"SELECT {COLS} FROM reactions {WHERE_VALID} AND id > ? ORDER BY id ASC LIMIT 1",
        [reaction_id],
    ).fetchone()
    if not row:
        # Wrap around to first
        row = conn.execute(
            f"SELECT {COLS} FROM reactions {WHERE_VALID} ORDER BY id ASC LIMIT 1"
        ).fetchone()
    conn.close()
    return dict(row)


@app.get("/api/reactions/{reaction_id}/prev")
def prev_reaction(reaction_id: int):
    conn = get_db()
    row = conn.execute(
        f"SELECT {COLS} FROM reactions {WHERE_VALID} AND id < ? ORDER BY id DESC LIMIT 1",
        [reaction_id],
    ).fetchone()
    if not row:
        # Wrap around to last
        row = conn.execute(
            f"SELECT {COLS} FROM reactions {WHERE_VALID} ORDER BY id DESC LIMIT 1"
        ).fetchone()
    conn.close()
    return dict(row)
