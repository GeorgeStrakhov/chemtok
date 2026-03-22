"""
Augment reaction database with LLM-generated metadata.

Reads from a source db, processes each reaction through an LLM,
writes results to a new augmented db.
Uses Groq SDK with qwen/qwen3-32b by default.
"""

import json
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from tqdm import tqdm

load_dotenv()

MODEL = os.getenv("LLM_MODEL", "qwen/qwen3-32b")
PROMPT_FILE = Path(__file__).parent / "data_augmentation_prompt.md"

client = Groq()

# JSON schema for Groq structured output
RESPONSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "reaction_augmentation",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "conditions": {"type": "string"},
                "named_reaction": {"type": "string"},
                "category": {
                    "type": "string",
                    "enum": [
                        "C-C bond formation",
                        "C-heteroatom bond formation",
                        "oxidation",
                        "reduction",
                        "protection",
                        "deprotection",
                        "functional group interconversion",
                        "ring formation",
                        "ring opening",
                        "rearrangement",
                        "elimination",
                        "addition",
                        "substitution",
                        "condensation",
                        "other",
                    ],
                },
                "difficulty": {
                    "type": "string",
                    "enum": [
                        "intro_organic",
                        "advanced_organic",
                        "graduate",
                        "research",
                    ],
                },
                "transform": {"type": "string"},
                "notes": {"type": "string"},
                "error": {"type": "string"},
            },
            "required": [
                "conditions",
                "named_reaction",
                "category",
                "difficulty",
                "transform",
                "notes",
                "error",
            ],
            "additionalProperties": False,
        },
    },
}


def load_system_prompt() -> str:
    return PROMPT_FILE.read_text()


def build_user_prompt(row: dict) -> str:
    parts = [f"Reactants: {row['reactants']}"]
    if row["conditions"]:
        parts.append(f"Conditions/Reagents: {row['conditions']}")
    parts.append(f"Product: {row['product']}")
    return "\n".join(parts)


def call_llm(system_prompt: str, user_prompt: str) -> dict | None:
    try:
        completion = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
            max_completion_tokens=4096,
            top_p=0.95,
            reasoning_effort="none",
            response_format={"type": "json_object"},
        )
        content = completion.choices[0].message.content or ""
        content = content.strip()
        # Strip <think>...</think> blocks (reasoning models)
        if "<think>" in content:
            content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return json.loads(content)
    except json.JSONDecodeError as e:
        tqdm.write(f"  JSON parse error: {e}\n  Raw: {content[:200]}")
        return None
    except Exception as e:
        tqdm.write(f"  LLM error: {e}")
        return None


def create_output_db(path: Path) -> sqlite3.Connection:
    if path.exists():
        path.unlink()
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE reactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            reactants TEXT NOT NULL,
            conditions TEXT NOT NULL DEFAULT '',
            product TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT '',
            named_reaction TEXT NOT NULL DEFAULT '',
            category TEXT NOT NULL DEFAULT '',
            difficulty TEXT NOT NULL DEFAULT '',
            transform TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            raw_conditions TEXT NOT NULL DEFAULT '',
            source_row TEXT NOT NULL DEFAULT '',
            error TEXT NOT NULL DEFAULT ''
        )
    """)
    conn.execute("CREATE INDEX idx_named_reaction ON reactions(named_reaction)")
    conn.execute("CREATE INDEX idx_category ON reactions(category)")
    conn.execute("CREATE INDEX idx_difficulty ON reactions(difficulty)")
    conn.commit()
    return conn


def augment(input_db: str, output_db: str, limit: int | None = None):
    system_prompt = load_system_prompt()

    src = sqlite3.connect(input_db)
    src.row_factory = sqlite3.Row

    # Detect if input is a clustered db (has clusters table) or regular reactions db
    tables = {r[0] for r in src.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    if "clusters" in tables:
        table = "clusters"
        id_col = "representative_id"
        print("Detected clustered input — augmenting representatives only")
    else:
        table = "reactions"
        id_col = "id"

    query = f"SELECT * FROM {table}"
    if limit:
        query += f" LIMIT {limit}"
    rows = src.execute(query).fetchall()

    out = create_output_db(Path(output_db))

    print(f"Augmenting {len(rows)} reactions using {MODEL}")
    print(f"Input:  {input_db}")
    print(f"Output: {output_db}\n")

    ok = 0
    errors = 0
    skipped = 0

    pbar = tqdm(rows, desc="Augmenting", unit="rxn")
    for row in pbar:
        row_dict = dict(row)
        user_prompt = build_user_prompt(row_dict)

        result = call_llm(system_prompt, user_prompt)

        if result is None:
            skipped += 1
            pbar.set_postfix(ok=ok, err=errors, skip=skipped)
            continue

        is_error = result.get("error", "") != ""

        source_row_json = json.dumps(row_dict, default=str)
        src_id = row_dict.get(id_col, row_dict.get("id"))

        if is_error:
            out.execute(
                """INSERT INTO reactions
                    (source_id, reactants, conditions, product, source, raw_conditions, source_row, error)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    src_id,
                    row_dict["reactants"],
                    row_dict["conditions"],
                    row_dict["product"],
                    row_dict.get("source", ""),
                    row_dict["conditions"],
                    source_row_json,
                    result["error"],
                ),
            )
            errors += 1
        else:
            out.execute(
                """INSERT INTO reactions
                    (source_id, reactants, conditions, product, source,
                     named_reaction, category, difficulty, transform, notes, raw_conditions, source_row)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    src_id,
                    row_dict["reactants"],
                    result.get("conditions", row_dict["conditions"]),
                    row_dict["product"],
                    row_dict.get("source", ""),
                    result.get("named_reaction", ""),
                    result.get("category", ""),
                    result.get("difficulty", ""),
                    result.get("transform", ""),
                    result.get("notes", ""),
                    row_dict["conditions"],
                    source_row_json,
                ),
            )
            ok += 1

        out.commit()
        pbar.set_postfix(ok=ok, err=errors, skip=skipped)
        time.sleep(0.1)

    src.close()
    out.close()

    print(f"\nDone. {ok} augmented, {errors} errors, {skipped} skipped.")
    print(f"Output: {output_db}")


if __name__ == "__main__":
    input_db = sys.argv[1] if len(sys.argv) > 1 else "data/reactions_sample100.db"
    output_db = sys.argv[2] if len(sys.argv) > 2 else input_db.replace(".db", "_augmented.db")
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else None
    augment(input_db, output_db, limit)
