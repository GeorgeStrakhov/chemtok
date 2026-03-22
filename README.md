# ChemTOK

TikTok for chemical reactions. Swipe through reactions, see reactants, guess the product (blur-reveal), learn conditions and named reactions.

**Live:** https://chemtok.org

## How it works

1. **Swipe** through reaction cards vertically
2. **See** the reactants and conditions
3. **Tap** to reveal the product (blur-reveal)
4. **Learn** the reaction type, category, and description
5. **Favorite** reactions to review later

## Data pipeline

We built a database of 543 augmented chemical reactions from two open sources:

| Source | Reactions | License |
|--------|-----------|---------|
| [USPTO/ORDerly](https://figshare.com/articles/dataset/Chemical_reactions_from_US_patents_1976-Sep2016_/5104873) | 669K | CC-0 |
| [CRD](https://figshare.com/articles/dataset/Reaction_SMILES_dataset/22491730) | 1.44M | CC BY 4.0 |

After merging and deduplication: **1.68M unique reactions**.

A sample was then augmented using an LLM (qwen3-32b via Groq) to add:
- **Human-readable conditions** — SMILES like `[H-].[Na+]` converted to `NaH`
- **Named reactions** — Suzuki coupling, Grignard, etc.
- **Categories** — C-C bond formation, reduction, substitution, etc.
- **Transform descriptions** — `aryl halide + boronic acid → biaryl`
- **Plain English notes**

### Pipeline scripts

```
build_db.py              # USPTO → reactions.db
crd/build_crd_db.py      # CRD → reactions_crd.db
merge_dbs.py             # Combine + deduplicate → reactions_all.db
augment.py               # LLM augmentation → augmented db
data_augmentation_prompt.md  # Prompt template
```

## Stack

- **Frontend:** React + TypeScript + Tailwind + shadcn/ui + smiles-drawer
- **Backend:** Cloudflare Worker + D1 (SQLite)
- **Data processing:** Python 3.11 + RDKit + Groq API
- **Package managers:** pnpm (JS), uv (Python)

## Development

```bash
# Python setup
uv sync

# Run local dev servers (FastAPI + Vite)
./dev.sh

# Or separately:
uv run uvicorn server:app --reload --port 8000
cd web && pnpm dev
```

## Deploy

```bash
# Build and deploy frontend + worker
cd web
pnpm build
npx wrangler deploy

# Update D1 database
sqlite3 ../data/reactions_augmented_combined.db .dump > worker/seed.sql
grep -v "^BEGIN TRANSACTION" worker/seed.sql | grep -v "^COMMIT" > worker/seed_clean.sql
npx wrangler d1 execute chemtok-db --remote --file=worker/seed_clean.sql
```

## License

Data: see individual source licenses above. Code: MIT.
