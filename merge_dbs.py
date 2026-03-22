"""
Merge USPTO and CRD reaction databases into a single deduplicated database.

When a reaction exists in both, prefers the USPTO version (has better condition labels).
"""

import sqlite3
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data"
USPTO_DB = DATA_DIR / "reactions.db"
CRD_DB = DATA_DIR / "reactions_crd.db"
OUTPUT_DB = DATA_DIR / "reactions_all.db"


def merge():
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()

    out = sqlite3.connect(OUTPUT_DB)
    cur = out.cursor()

    cur.execute("""
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            reactants TEXT NOT NULL,
            conditions TEXT NOT NULL DEFAULT '',
            product TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT '',
            dedup_key TEXT UNIQUE NOT NULL
        )
    """)
    cur.execute("CREATE INDEX idx_name ON reactions(name)")
    cur.execute("CREATE INDEX idx_source ON reactions(source)")

    seen = set()
    inserted = 0

    # USPTO first (preferred — has human-readable conditions)
    print("Loading USPTO...")
    uspto = sqlite3.connect(USPTO_DB)
    rows = uspto.execute("SELECT name, reactants, conditions, product, dedup_key FROM reactions").fetchall()
    batch = []
    for name, reactants, conditions, product, key in rows:
        if key in seen:
            continue
        seen.add(key)
        batch.append((name, reactants, conditions, product, "uspto", key))
    cur.executemany(
        "INSERT INTO reactions (name, reactants, conditions, product, source, dedup_key) VALUES (?, ?, ?, ?, ?, ?)",
        batch,
    )
    inserted += len(batch)
    print(f"  USPTO: {inserted:,} inserted")
    uspto.close()

    # CRD second (skip duplicates)
    print("Loading CRD...")
    crd = sqlite3.connect(CRD_DB)
    crd_rows = crd.execute("SELECT name, reactants, conditions, product, dedup_key FROM reactions").fetchall()
    batch = []
    skipped = 0
    for name, reactants, conditions, product, key in crd_rows:
        if key in seen:
            skipped += 1
            continue
        seen.add(key)
        batch.append((name, reactants, conditions, product, "crd", key))
        if len(batch) >= 10000:
            cur.executemany(
                "INSERT INTO reactions (name, reactants, conditions, product, source, dedup_key) VALUES (?, ?, ?, ?, ?, ?)",
                batch,
            )
            inserted += len(batch)
            batch.clear()
    if batch:
        cur.executemany(
            "INSERT INTO reactions (name, reactants, conditions, product, source, dedup_key) VALUES (?, ?, ?, ?, ?, ?)",
            batch,
        )
        inserted += len(batch)
    print(f"  CRD: {inserted - len([r for r in rows]):,} new, {skipped:,} duplicates skipped")
    crd.close()

    out.commit()

    total = cur.execute("SELECT COUNT(*) FROM reactions").fetchone()[0]
    by_source = cur.execute("SELECT source, COUNT(*) FROM reactions GROUP BY source").fetchall()
    print(f"\nTotal: {total:,}")
    for source, count in by_source:
        print(f"  {source}: {count:,}")

    out.close()
    print(f"\nSaved to {OUTPUT_DB}")


if __name__ == "__main__":
    merge()
