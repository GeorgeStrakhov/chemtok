import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Heart, Bug } from "lucide-react";
import { MoleculeGroup } from "./MoleculeGroup";
import type { Reaction } from "@/types/reaction";

const DIFFICULTY_LABEL: Record<string, string> = {
  intro_organic: "Intro",
  advanced_organic: "Advanced",
  graduate: "Graduate",
  research: "Research",
};

interface Props {
  reaction: Reaction;
  isFavorite: boolean;
  onToggleFavorite: () => void;
  dark?: boolean;
}

function JsonBlock({ label, data }: { label: string; data: string }) {
  const copy = () => {
    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(data);
    } else {
      const ta = document.createElement("textarea");
      ta.value = data;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }
  };
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-muted-foreground uppercase">
          {label}
        </span>
        <Button variant="ghost" size="sm" className="h-6 text-xs" onClick={copy}>
          Copy
        </Button>
      </div>
      <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-60 whitespace-pre-wrap break-all">
        {data}
      </pre>
    </div>
  );
}

export function ReactionCard({
  reaction,
  isFavorite,
  onToggleFavorite,
  dark,
}: Props) {
  const [debugOpen, setDebugOpen] = useState(false);

  const title =
    reaction.named_reaction && reaction.named_reaction !== "none"
      ? reaction.named_reaction
      : reaction.transform || `Reaction #${reaction.id}`;

  // Build the augmented JSON (without source_row to keep it clean)
  const { source_row: _sr, raw_conditions: _rc, ...augmented } = reaction;
  const augmentedJson = JSON.stringify(augmented, null, 2);
  const originalJson = reaction.source_row
    ? JSON.stringify(JSON.parse(reaction.source_row), null, 2)
    : "{}";

  return (
    <>
      <Card className="flex flex-col max-h-[calc(100dvh-7rem)] overflow-hidden">
        <CardContent className="flex flex-col flex-1 gap-2 p-4 overflow-y-auto">
          {/* Header */}
          <div className="flex items-start justify-between shrink-0">
            <div className="flex-1 min-w-0">
              <h2 className="text-sm font-semibold text-foreground leading-tight truncate">
                {title}
              </h2>
              <div className="flex gap-2 mt-1 flex-wrap">
                {reaction.category && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground">
                    {reaction.category}
                  </span>
                )}
                {reaction.difficulty && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground">
                    {DIFFICULTY_LABEL[reaction.difficulty] ?? reaction.difficulty}
                  </span>
                )}
              </div>
            </div>
            <div className="flex gap-0 shrink-0">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setDebugOpen(true);
                }}
                className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
              >
                <Bug className="w-4 h-4 text-muted-foreground" />
              </button>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleFavorite();
                }}
                className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
              >
                <Heart
                  className={`w-5 h-5 transition-colors ${
                    isFavorite
                      ? "fill-red-500 text-red-500"
                      : "text-muted-foreground"
                  }`}
                />
              </button>
            </div>
          </div>

          {/* Reactants */}
          <div className="flex justify-center shrink-0">
            <MoleculeGroup smiles={reaction.reactants} dark={dark} />
          </div>

          {/* Arrow + Conditions */}
          <div className="flex flex-col items-center shrink-0">
            <div className="text-xl text-muted-foreground select-none">↓</div>
            {reaction.conditions && (
              <p className="text-xs text-muted-foreground italic text-center px-4 leading-snug">
                {reaction.conditions}
              </p>
            )}
          </div>

          {/* Product */}
          <div className="flex justify-center shrink-0">
            <MoleculeGroup smiles={reaction.product} dark={dark} />
          </div>

          {/* Notes */}
          {reaction.notes && (
            <p className="text-xs text-muted-foreground text-center px-2 shrink-0">
              {reaction.notes}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Debug dialog */}
      <Dialog open={debugOpen} onOpenChange={setDebugOpen}>
        <DialogContent className="max-w-lg max-h-[85dvh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-sm">
              Debug — Reaction #{reaction.id}
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <JsonBlock label="Original (pre-augmentation)" data={originalJson} />
            <JsonBlock label="Augmented" data={augmentedJson} />
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
