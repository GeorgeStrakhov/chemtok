declare module "smiles-drawer" {
  interface DrawerOptions {
    width?: number;
    height?: number;
    bondThickness?: number;
    shortBondLength?: number;
    bondLength?: number;
    padding?: number;
    compactDrawing?: boolean;
    fontSizeLarge?: number;
    fontSizeSmall?: number;
  }

  class SvgDrawer {
    constructor(options?: DrawerOptions);
    draw(
      tree: unknown,
      target: string | SVGElement,
      theme?: string,
      onlyComputeProperties?: boolean
    ): void;
  }

  class Drawer {
    constructor(options?: DrawerOptions);
    draw(
      tree: unknown,
      target: string | HTMLCanvasElement,
      theme?: string,
      onlyComputeProperties?: boolean
    ): void;
  }

  function parse(
    smiles: string,
    onSuccess: (tree: unknown) => void,
    onError: (err: unknown) => void
  ): void;

  export { SvgDrawer, Drawer, parse };
  export default { SvgDrawer, Drawer, parse };
}
