import { MoleculeRenderer } from "./MoleculeRenderer";

interface Props {
  smiles: string;
  dark?: boolean;
}

export function MoleculeGroup({ smiles, dark }: Props) {
  const parts = smiles.split(".");

  return (
    <div className="flex items-center justify-center gap-1 flex-wrap">
      {parts.map((smi, i) => (
        <div key={i} className="flex items-center gap-1">
          {i > 0 && (
            <span className="text-lg text-muted-foreground">+</span>
          )}
          <MoleculeRenderer smiles={smi} dark={dark} />
        </div>
      ))}
    </div>
  );
}
