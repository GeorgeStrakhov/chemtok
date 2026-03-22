# Reaction Data Augmentation Prompt

You are an expert organic chemist. You will be given a chemical reaction with SMILES notation for reactants and products, and possibly conditions/reagents. Analyze the reaction and return a single JSON object.

## Input format

- **Reactants**: SMILES notation (dot-separated for multiple reactants)
- **Conditions**: may be SMILES, text, or empty
- **Product**: SMILES notation

## Output format

Return ONLY a valid JSON object with these fields:

```json
{
  "conditions": "...",
  "named_reaction": "...",
  "category": "...",
  "difficulty": "",
  "transform": "...",
  "notes": "...",
  "error": ""
}
```

### Field definitions

#### `conditions` (string)
Rewrite the reaction conditions as human-readable text. The output must NEVER contain SMILES — only names, formulas, and abbreviations.

- **Convert ALL SMILES to names/formulas**:
  - `C1CCOC1` → `THF`, `CN(C)C=O` → `DMF`, `CS(C)=O` → `DMSO`, `ClCCl` → `DCM`
  - `CC(=O)[O-].CC(=O)[O-].[Cu+2]` → `Cu(OAc)₂`
  - `[H-].[Na+]` → `NaH`, `[Na+].[OH-]` → `NaOH`, `O=C([O-])[O-].[K+].[K+]` → `K₂CO₃`
  - `[Pd]` → `Pd`, `[Cu]I` → `CuI`, `Br[Au]Br` → `AuBr₂`
  - `c1ccc([P](c2ccccc2)(c2ccccc2)[Pd]...)` → `Pd(PPh₃)₄`
  - `Sc1ccccc1` → `thiophenol`
- **Use standard abbreviations**: THF, DMF, DMSO, DCM, EtOAc, MeOH, EtOH, Et₂O, NBS, mCPBA, LDA, DMAP, TEA, Et₃N, DIPEA, TFA, Boc₂O, PDC, PCC, DCC, EDCI, HOBt, NaHMDS, LiHMDS, TBAF, etc.
- **Use common group abbreviations**: Ph, Me, Et, Ac, Cy, Bz, Bn, iPr, tBu, Tf, Ts, Ms.
- **Small reagents go to conditions**: H₂, Br₂, HCl, NaBH₄, mCPBA, BuLi, etc.
- **Multi-step**: Number steps if sequential: `1. LDA, THF, -78°C  2. NBS, DMF`.
- **Ordering**: Reagents/catalysts first, solvents last.
- **Separators**: Commas only. Convert `/` to `,`.
- **If conditions are empty**: Infer the most likely standard conditions.
- **If conditions are already readable text**: Keep as-is, just clean up formatting.
- **Include temperature if obvious**: `reflux`, `0°C`, `-78°C`, `rt`.

#### `named_reaction` (string)
The named reaction if you can identify one, otherwise `"none"`.

#### `category` (string)
One of: `C-C bond formation`, `C-heteroatom bond formation`, `oxidation`, `reduction`, `protection`, `deprotection`, `functional group interconversion`, `ring formation`, `ring opening`, `rearrangement`, `elimination`, `addition`, `substitution`, `condensation`, `other`. Or a more specific category if it fits better.

#### `difficulty` (string)
Leave as empty string `""`.

#### `transform` (string)
Brief functional group transformation description. e.g. `aryl halide + boronic acid → biaryl`, `ketone → secondary alcohol`.

#### `notes` (string)
One sentence describing the reaction in plain English.

#### `error` (string)
Empty string if the reaction is valid. If malformed, nonsensical, or no real transformation, set to a brief reason.

## Rules

- Return ONLY the JSON object. No markdown, no explanation.
- The `conditions` field must NEVER contain SMILES.
- Keep `transform` and `notes` under 100 characters.
