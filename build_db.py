"""
Build SQLite database of chemical reactions from ORDerly condition dataset.

Parses ORDerly parquet data, converts SMILES to names where possible,
deduplicates, and loads into an SQLite database.
"""

import hashlib
import sqlite3
from pathlib import Path

import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors

RDLogger.logger().setLevel(RDLogger.ERROR)

DATA_DIR = Path(__file__).parent / "data"
ORDERLY_DIR = DATA_DIR / "23298467"
OUTPUT_DB = DATA_DIR / "reactions.db"

# Common solvents/reagents: SMILES -> human-readable name
KNOWN_COMPOUNDS = {
    "ClCCl": "DCM",
    "C(Cl)Cl": "DCM",
    "CO": "MeOH",
    "CCO": "EtOH",
    "CC(C)=O": "Acetone",
    "CC(=O)O": "AcOH",
    "CC#N": "MeCN",
    "CCCCCC": "Hexane",
    "c1ccncc1": "Pyridine",
    "c1ccoc1": "Furan",
    "C1CCOC1": "THF",
    "CCOCC": "Et2O",
    "O": "Water",
    "CS(C)=O": "DMSO",
    "CN(C)C=O": "DMF",
    "c1ccccc1": "Benzene",
    "Cc1ccccc1": "Toluene",
    "ClC(Cl)Cl": "Chloroform",
    "CCOC(C)=O": "EtOAc",
    "CC(C)O": "i-PrOH",
    "CCCCO": "n-BuOH",
    "C1COCCO1": "Dioxane",
    "CCCCCCCC": "Octane",
    "CC(C)CO": "i-BuOH",
    "C(=O)=O": "CO2",
    "N": "NH3",
    "[Na+].[OH-]": "NaOH",
    "O=C([O-])[O-].[Na+].[Na+]": "Na2CO3",
    "[K+].[OH-]": "KOH",
    "O=C([O-])O.[Na+]": "NaHCO3",
    "[Na+].[H-]": "NaH",
    "CCN(CC)CC": "Et3N",
    "c1ccc(P(c2ccccc2)c2ccccc2)cc1": "PPh3",
    "O=C1CCC(=O)N1Br": "NBS",
    "O=C1CCC(=O)N1Cl": "NCS",
    "[Pd]": "Pd",
    "Cl[Pd]Cl": "PdCl2",
    "[Li+].CCCC[Cu-]CCCC": "n-BuLi/CuI",
    "CCCC[Li]": "n-BuLi",
    "[Li+].[AlH4-]": "LiAlH4",
    "[Na+].[BH4-]": "NaBH4",
    "O=[Cr](=O)(O)O": "CrO3",
    "CC(=O)OO": "Peracetic acid",
    "OO": "H2O2",
}


def canonicalize(smi: str) -> str | None:
    if not smi or pd.isna(smi):
        return None
    mol = Chem.MolFromSmiles(smi)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)


def smiles_to_name(smi: str) -> str:
    """Try to resolve a SMILES to a human-readable name."""
    canon = canonicalize(smi)
    if canon and canon in KNOWN_COMPOUNDS:
        return KNOWN_COMPOUNDS[canon]
    return smi  # fallback to SMILES


def build_conditions(row) -> str:
    """Build a human-readable conditions string from agents, solvents, temperature."""
    parts = []

    # Agents (reagents/catalysts)
    for col in ["agent_000", "agent_001", "agent_002"]:
        val = row.get(col)
        if val and pd.notna(val):
            parts.append(smiles_to_name(val))

    # Solvents
    solvents = []
    for col in ["solvent_000", "solvent_001"]:
        val = row.get(col)
        if val and pd.notna(val):
            solvents.append(smiles_to_name(val))
    if solvents:
        parts.append("/".join(solvents))

    # Temperature
    temp = row.get("temperature")
    if pd.notna(temp):
        temp = float(temp)
        if temp <= 0:
            parts.append(f"{temp:.0f}°C")
        elif temp >= 50:
            parts.append(f"{temp:.0f}°C")
        else:
            parts.append(f"{temp:.0f}°C")

    return ", ".join(parts)


def dedup_key(reactants: str, product: str) -> str:
    raw = f"{reactants}||{product}"
    return hashlib.sha256(raw.encode()).hexdigest()


def build_database():
    print("Loading ORDerly condition dataset...")
    train = pd.read_parquet(ORDERLY_DIR / "orderly_condition_train.parquet")
    test = pd.read_parquet(ORDERLY_DIR / "orderly_condition_test.parquet")
    df = pd.concat([train, test], ignore_index=True)
    print(f"Total rows: {len(df)}")

    reactions = []
    skipped = 0
    duplicates = 0
    seen_keys = set()

    for _, row in df.iterrows():
        # Canonicalize reactants
        reactant_parts = []
        for col in ["reactant_000", "reactant_001"]:
            val = row.get(col)
            if val and pd.notna(val):
                c = canonicalize(val)
                if c:
                    reactant_parts.append(c)

        if not reactant_parts:
            skipped += 1
            continue

        # Canonicalize product
        product = canonicalize(row.get("product_000"))
        if not product:
            skipped += 1
            continue

        reactant_parts.sort()
        reactants = ".".join(reactant_parts)

        # Dedup
        key = dedup_key(reactants, product)
        if key in seen_keys:
            duplicates += 1
            continue
        seen_keys.add(key)

        conditions = build_conditions(row)

        reactions.append({
            "name": "",  # will be enriched later with reaction classification
            "reactants": reactants,
            "conditions": conditions,
            "product": product,
            "dedup_key": key,
        })

        if len(reactions) % 50000 == 0:
            print(f"  Processed {len(reactions)} unique reactions...")

    print(f"\nParsed: {len(reactions)} unique reactions")
    print(f"Skipped (invalid): {skipped}")
    print(f"Duplicates removed: {duplicates}")

    # Write to SQLite
    print(f"\nWriting to {OUTPUT_DB}...")
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

    cur.executemany(
        "INSERT INTO reactions (name, reactants, conditions, product, dedup_key) VALUES (?, ?, ?, ?, ?)",
        [(r["name"], r["reactants"], r["conditions"], r["product"], r["dedup_key"]) for r in reactions],
    )

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM reactions")
    total = cur.fetchone()[0]
    print(f"\nTotal reactions in DB: {total}")

    cur.execute("SELECT COUNT(*) FROM reactions WHERE conditions != ''")
    with_conds = cur.fetchone()[0]
    print(f"Reactions with conditions: {with_conds} ({100*with_conds/total:.1f}%)")

    print("\nSample entries:")
    cur.execute("SELECT reactants, conditions, product FROM reactions WHERE conditions != '' LIMIT 5")
    for row in cur.fetchall():
        print(f"  reactants: {row[0][:70]}")
        print(f"  conditions: {row[1]}")
        print(f"  product:    {row[2][:70]}")
        print()

    conn.close()
    print(f"Done! Database saved to {OUTPUT_DB}")


if __name__ == "__main__":
    build_database()
