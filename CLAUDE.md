# ChemTOK

Educational chemistry app — "TikTok for chemical reactions." Swipe through reactions, see reactants, guess the product (blur-reveal), learn conditions and named reactions.

## Project Structure

```
chem-fil/
├── web/                          # Frontend + Cloudflare Worker (deployed together)
│   ├── src/                      # React app (Vite + TypeScript + Tailwind + shadcn/ui)
│   │   ├── components/
│   │   │   ├── SwipeContainer.tsx   # TikTok-style vertical swipe navigation
│   │   │   ├── ReactionCard.tsx     # Card with blur-reveal, favorites, metadata
│   │   │   ├── MoleculeRenderer.tsx # SMILES → SVG via smiles-drawer v2 (SvgDrawer)
│   │   │   ├── MoleculeGroup.tsx    # Renders multi-component SMILES (A.B → A + B)
│   │   │   └── ui/                  # shadcn/ui components (button, card)
│   │   ├── hooks/
│   │   │   ├── useFavorites.ts      # localStorage-backed favorites
│   │   │   └── useTheme.ts         # Dark/light mode toggle
│   │   ├── services/api.ts         # API client (fetch wrappers)
│   │   └── types/reaction.ts       # Reaction type definition
│   ├── worker/
│   │   ├── index.ts               # Cloudflare Worker — serves API from D1
│   │   ├── seed.sql               # Full DB dump for seeding D1
│   │   └── seed_clean.sql         # Same without BEGIN/COMMIT (D1 compatible)
│   ├── wrangler.jsonc             # Cloudflare config (account, D1 binding)
│   ├── vite.config.ts             # Vite + Tailwind + tsconfig paths
│   └── package.json               # pnpm
│
├── data/                          # Local SQLite databases (not deployed)
│   ├── reactions_sample100_augmented.db  # ★ Current production DB (100 augmented reactions)
│   ├── reactions.db                      # 669K reactions from ORDerly (USPTO patents)
│   ├── reactions_all.db                  # Merged DB
│   ├── reactions_crd.db                  # CRD dataset
│   ├── reactions_sample100.db            # Pre-augmentation sample
│   └── USPTO_50K.csv                     # Raw USPTO-50K download
│
├── data/23298467/                 # ORDerly benchmark parquet files (1.8GB, not committed)
│
├── old_fokke/                     # Original vanilla JS prototype (reference only)
│   ├── index.html                 # Full app in single HTML file
│   ├── reactions.json             # 85 curated reactions
│   ├── dictionary.json            # Reagent name ↔ SMILES lookup
│   ├── highschool_reactions_smiles.json
│   └── bachelors_reactions_smiles.json
│
├── build_db.py                    # Builds reactions.db from ORDerly parquet data
├── augment.py                     # LLM augmentation script (adds named_reaction, category, etc.)
├── cluster_reactions.py           # Reaction clustering/sampling
├── merge_dbs.py                   # Merges multiple DBs
├── data_augmentation_prompt.md    # Prompt template for LLM augmentation
├── server.py                      # Local dev FastAPI server
├── dev.sh                         # Runs both FastAPI + Vite dev servers
└── pyproject.toml                 # Python deps (uv, Python 3.11, rdkit, pandas, etc.)
```

## Database Schema (augmented)

```sql
CREATE TABLE reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER,
    reactants TEXT NOT NULL,          -- SMILES (dot-separated for multiple)
    conditions TEXT NOT NULL,          -- Human-readable: "Pd(PPh₃)₄, K₂CO₃, DMF"
    product TEXT NOT NULL,             -- SMILES
    source TEXT NOT NULL DEFAULT '',
    named_reaction TEXT NOT NULL DEFAULT '',  -- e.g. "Suzuki coupling" or "none"
    category TEXT NOT NULL DEFAULT '',        -- e.g. "C-C bond formation"
    difficulty TEXT NOT NULL DEFAULT '',      -- intro_organic / advanced_organic / graduate / research
    transform TEXT NOT NULL DEFAULT '',       -- e.g. "aryl halide + boronic acid → biaryl"
    notes TEXT NOT NULL DEFAULT '',           -- One-sentence description
    raw_conditions TEXT NOT NULL DEFAULT '',
    error TEXT NOT NULL DEFAULT ''            -- Non-empty = skip this row
);
```

## Commands

### Local development
```bash
./dev.sh                    # Starts FastAPI (port 8000) + Vite (port 5173)
```

### Deploy to Cloudflare
```bash
cd web
pnpm build                  # Build React app → dist/
npx wrangler deploy         # Deploy Worker + static assets
```

### Seed/update D1 database
```bash
cd web
# Export local DB to SQL:
sqlite3 ../data/reactions_sample100_augmented.db .dump > worker/seed.sql
# Clean for D1 (no transactions):
grep -v "^BEGIN TRANSACTION" worker/seed.sql | grep -v "^COMMIT" > worker/seed_clean.sql
# Push to remote D1:
npx wrangler d1 execute chemtok-db --remote --file=worker/seed_clean.sql
```

### Build reaction database from scratch
```bash
uv run python build_db.py   # Parse ORDerly → reactions.db (669K reactions)
uv run python augment.py    # LLM-augment a sample with named reactions, categories, etc.
```

## Deployment

- **URL**: https://chemtok.move38.workers.dev
- **Cloudflare account**: move38 (a7b1e373a9581b6f04e2a48d3abc9aa3)
- **D1 database**: chemtok-db (61d4f5db-ca95-4a14-b49a-b5e0106a80f5)
- **Region**: WEUR (Western Europe)

## Data Sources & Licensing

- **USPTO/Lowe dataset** (CC-0, public domain) — 50K classified reactions, no conditions
- **ORDerly** (CC-BY-SA 4.0) — 669K reactions with conditions/solvents/temperature from Open Reaction Database
- **CRD** (unclear license) — 1.44M reactions, not used in production

## Key Technical Decisions

- **smiles-drawer v2** with `SvgDrawer` — SVGs scale naturally, no canvas sizing issues. Pass DOM element (not ID string) to `draw()`.
- **Python 3.11** pinned — rdkit-pypi doesn't have wheels for 3.12+
- **uv** for all Python tooling
- **pnpm** for JS package management
- Inline styles in React components map easily to React Native's `StyleSheet.create` for future mobile port
- `MoleculeRenderer` is the only web-specific component (canvas/SVG) — swap for WebView in RN

## Next Steps

- Scale to 10K+ augmented reactions (run augment.py on larger sample from reactions.db)
- Add filtering by category/difficulty in the swipe UI
- Port to React Native for mobile app
- Consider adding the dictionary system from old_fokke (clickable reagent names → structure popups)
