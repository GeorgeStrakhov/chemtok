"""
Cluster reactions by reaction fingerprint to find unique "templates".

Uses RDKit structural reaction fingerprints, hashed to buckets.
Reactions with identical fingerprint bit patterns get the same cluster.
Outputs a db of cluster representatives (one per cluster), prioritizing
reactions that have conditions.
"""

import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

from rdkit import RDLogger
from rdkit.Chem import AllChem
from tqdm import tqdm

RDLogger.logger().setLevel(RDLogger.ERROR)

INPUT_DB = Path("data/reactions_all.db")
OUTPUT_DB = Path("data/reactions_clustered.db")


def reaction_fingerprint_key(reactants: str, product: str) -> str | None:
    """Compute a hashable fingerprint key for a reaction."""
    try:
        rxn_smiles = f"{reactants}>>{product}"
        rxn = AllChem.ReactionFromSmarts(rxn_smiles, useSmiles=True)
        if rxn is None:
            return None
        fp = AllChem.CreateStructuralFingerprintForReaction(rxn)
        return fp.ToBitString()
    except Exception:
        return None


def cluster(input_db: str = None, output_db: str = None, conditions_only: bool = True):
    input_db = Path(input_db) if input_db else INPUT_DB
    output_db = Path(output_db) if output_db else OUTPUT_DB

    conn = sqlite3.connect(input_db)
    conn.row_factory = sqlite3.Row

    where = "WHERE conditions != ''" if conditions_only else ""
    total = conn.execute(f"SELECT COUNT(*) FROM reactions {where}").fetchone()[0]
    print(f"Processing {total:,} reactions from {input_db}")
    if conditions_only:
        print("(only reactions with conditions)")

    rows = conn.execute(f"SELECT * FROM reactions {where}")

    # Group by fingerprint
    clusters = defaultdict(list)  # fp_key -> [row_ids]
    skipped = 0

    for row in tqdm(rows, total=total, desc="Fingerprinting", unit="rxn"):
        row_dict = dict(row)
        fp_key = reaction_fingerprint_key(row_dict["reactants"], row_dict["product"])
        if fp_key is None:
            skipped += 1
            continue
        clusters[fp_key].append(row_dict)

    conn.close()

    print(f"\nFingerprinted: {total - skipped:,}")
    print(f"Skipped (invalid): {skipped:,}")
    print(f"Unique clusters: {len(clusters):,}")

    # Pick representative per cluster: prefer one with non-empty conditions
    if output_db.exists():
        output_db.unlink()
    out = sqlite3.connect(output_db)
    out.execute("""
        CREATE TABLE clusters (
            cluster_id INTEGER PRIMARY KEY AUTOINCREMENT,
            representative_id INTEGER NOT NULL,
            cluster_size INTEGER NOT NULL,
            reactants TEXT NOT NULL,
            conditions TEXT NOT NULL DEFAULT '',
            product TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT ''
        )
    """)
    out.execute("CREATE INDEX idx_rep_id ON clusters(representative_id)")

    # Also store all members for later propagation
    out.execute("""
        CREATE TABLE cluster_members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cluster_id INTEGER NOT NULL,
            reaction_id INTEGER NOT NULL,
            FOREIGN KEY (cluster_id) REFERENCES clusters(cluster_id)
        )
    """)
    out.execute("CREATE INDEX idx_cm_cluster ON cluster_members(cluster_id)")

    cluster_sizes = []
    for fp_key, members in tqdm(clusters.items(), desc="Writing clusters", unit="cluster"):
        # Pick best representative: prefer conditions, then shortest SMILES (simpler molecule)
        members.sort(key=lambda r: (r["conditions"] == "", len(r["reactants"])))
        rep = members[0]

        out.execute(
            "INSERT INTO clusters (representative_id, cluster_size, reactants, conditions, product, source) VALUES (?, ?, ?, ?, ?, ?)",
            (rep["id"], len(members), rep["reactants"], rep["conditions"], rep["product"], rep.get("source", "")),
        )
        cluster_id = out.execute("SELECT last_insert_rowid()").fetchone()[0]

        out.executemany(
            "INSERT INTO cluster_members (cluster_id, reaction_id) VALUES (?, ?)",
            [(cluster_id, m["id"]) for m in members],
        )
        cluster_sizes.append(len(members))

    out.commit()

    # Stats
    cluster_sizes.sort(reverse=True)
    print(f"\nCluster size distribution:")
    print(f"  Total clusters: {len(cluster_sizes):,}")
    print(f"  Singletons (size=1): {sum(1 for s in cluster_sizes if s == 1):,}")
    print(f"  Top 10 largest: {cluster_sizes[:10]}")
    print(f"  Median size: {cluster_sizes[len(cluster_sizes)//2]}")
    print(f"  Reactions covered: {sum(cluster_sizes):,}")

    out.close()
    print(f"\nSaved to {output_db}")


if __name__ == "__main__":
    input_db = sys.argv[1] if len(sys.argv) > 1 else None
    output_db = sys.argv[2] if len(sys.argv) > 2 else None
    cluster(input_db, output_db)
