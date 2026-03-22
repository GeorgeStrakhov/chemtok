import { useRef, useEffect } from "react";
import SmilesDrawer from "smiles-drawer";

const svgDrawer = new SmilesDrawer.SvgDrawer({ compactDrawing: false });

interface Props {
  smiles: string;
  dark?: boolean;
}

export function MoleculeRenderer({ smiles, dark = false }: Props) {
  const containerRef = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    el.innerHTML = "";
    el.appendChild(svg);

    const theme = dark ? "dark" : "light";

    SmilesDrawer.parse(
      smiles,
      (tree: unknown) => {
        svgDrawer.draw(tree, svg, theme, false);
        // Set viewBox from rendered content so SVG scales to fit
        const bbox = svg.getBBox();
        if (bbox.width > 0 && bbox.height > 0) {
          svg.setAttribute(
            "viewBox",
            `${bbox.x - 10} ${bbox.y - 10} ${bbox.width + 20} ${bbox.height + 20}`
          );
          svg.removeAttribute("width");
          svg.removeAttribute("height");
          svg.style.width = "100%";
          svg.style.height = "100%";
        }
      },
      () => {
        el.innerHTML = `<span class="text-xs text-muted-foreground">Invalid SMILES</span>`;
      }
    );
  }, [smiles, dark]);

  return (
    <span
      ref={containerRef}
      className="inline-flex items-center justify-center w-[140px] h-[100px] sm:w-[160px] sm:h-[120px]"
    />
  );
}
