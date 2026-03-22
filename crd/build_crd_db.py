"""
Build SQLite database of chemical reactions from the CRD dataset (1.44M reactions).

Parses reaction SMILES (reactants>reagents>products), canonicalizes with RDKit,
deduplicates, and loads into SQLite.

Source: https://figshare.com/articles/dataset/Reaction_SMILES_CRD_1_44M_dataset/30978826
License: CC BY 4.0
"""

import hashlib
import sqlite3
from pathlib import Path

from rdkit import Chem, RDLogger

RDLogger.logger().setLevel(RDLogger.ERROR)

CRD_DIR = Path(__file__).parent
INPUT_FILE = CRD_DIR / "reactionSmilesFigShare2025.txt"
OUTPUT_DB = Path(__file__).parent.parent / "data" / "reactions_crd.db"


def canonicalize_smiles(smi: str) -> str | None:
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def parse_reaction(line: str) -> dict | None:
    """Parse 'reactants>reagents>products' into components."""
    parts = line.split(">")
    if len(parts) != 3:
        return None

    reactants_smi, reagents_smi, products_smi = parts

    if not reactants_smi or not products_smi:
        return None

    # Canonicalize reactants
    canon_reactants = []
    for r in reactants_smi.split("."):
        cr = canonicalize_smiles(r.strip())
        if cr:
            canon_reactants.append(cr)
    if not canon_reactants:
        return None

    # Canonicalize products (take all)
    canon_products = []
    for p in products_smi.split("."):
        cp = canonicalize_smiles(p.strip())
        if cp:
            canon_products.append(cp)
    if not canon_products:
        return None

    # Reagents as conditions
    conditions = ""
    if reagents_smi.strip():
        canon_reagents = []
        for rg in reagents_smi.split("."):
            crg = canonicalize_smiles(rg.strip())
            if crg:
                canon_reagents.append(crg)
        if canon_reagents:
            conditions = ".".join(sorted(canon_reagents))

    canon_reactants.sort()
    canon_products.sort()

    return {
        "reactants": ".".join(canon_reactants),
        "product": ".".join(canon_products),
        "conditions": conditions,
    }


def dedup_key(reactants: str, product: str) -> str:
    raw = f"{reactants}||{product}"
    return hashlib.sha256(raw.encode()).hexdigest()


def build_database():
    print(f"Reading {INPUT_FILE}...")

    if not INPUT_FILE.exists():
        print(f"ERROR: {INPUT_FILE} not found. Download from Figshare first.")
        return

    OUTPUT_DB.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()

    conn = sqlite3.connect(OUTPUT_DB)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL DEFAULT '',
            reactants TEXT NOT NULL,
            conditions TEXT NOT NULL DEFAULT '',
            product TEXT NOT NULL,
            dedup_key TEXT UNIQUE NOT NULL
        )
    """)
    cur.execute("CREATE INDEX idx_name ON reactions(name)")

    seen_keys = set()
    inserted = 0
    skipped = 0
    duplicates = 0
    batch = []
    BATCH_SIZE = 5000

    with open(INPUT_FILE) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue

            parsed = parse_reaction(line)
            if parsed is None:
                skipped += 1
                continue

            key = dedup_key(parsed["reactants"], parsed["product"])
            if key in seen_keys:
                duplicates += 1
                continue
            seen_keys.add(key)

            batch.append((
                "", parsed["reactants"], parsed["conditions"],
                parsed["product"], key,
            ))

            if len(batch) >= BATCH_SIZE:
                cur.executemany(
                    "INSERT INTO reactions (name, reactants, conditions, product, dedup_key) VALUES (?, ?, ?, ?, ?)",
                    batch,
                )
                inserted += len(batch)
                batch.clear()
                if inserted % 100000 == 0:
                    print(f"  ...{inserted:,} inserted ({i:,} lines processed)")

    if batch:
        cur.executemany(
            "INSERT INTO reactions (name, reactants, conditions, product, dedup_key) VALUES (?, ?, ?, ?, ?)",
            batch,
        )
        inserted += len(batch)

    conn.commit()

    print(f"\nTotal lines processed: {i:,}")
    print(f"Inserted: {inserted:,}")
    print(f"Skipped (invalid): {skipped:,}")
    print(f"Duplicates removed: {duplicates:,}")

    # Sample
    print("\nSample entries:")
    cur.execute("SELECT reactants, conditions, product FROM reactions LIMIT 3")
    for row in cur.fetchall():
        print(f"  reactants: {row[0][:80]}...")
        print(f"  conditions: {row[1][:80]}")
        print(f"  product: {row[2][:80]}")
        print()

    conn.close()
    print(f"Done! Database saved to {OUTPUT_DB}")


if __name__ == "__main__":
    build_database()
