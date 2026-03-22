import { Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { SwipeContainer } from "@/components/SwipeContainer";
import { useFavorites } from "@/hooks/useFavorites";
import { useTheme } from "@/hooks/useTheme";

export default function App() {
  const { toggle: toggleFavorite, isFavorite } = useFavorites();
  const { dark, toggle: toggleTheme } = useTheme();

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b">
        <h1 className="text-lg font-bold tracking-tight">ChemTOK</h1>
        <Button variant="ghost" size="icon" onClick={toggleTheme}>
          {dark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
        </Button>
      </header>

      {/* Swipe area */}
      <SwipeContainer
        isFavorite={isFavorite}
        onToggleFavorite={toggleFavorite}
        dark={dark}
      />

      {/* Footer */}
      <footer className="text-center text-xs text-muted-foreground pb-4 px-4 space-y-1">
        <div>Swipe up for next &middot; Swipe down for previous</div>
        <div>
          Feedback? <a href="mailto:phil@chemtok.org" className="underline hover:text-foreground">phil@chemtok.org</a>
        </div>
        <div className="pt-1 text-[10px] opacity-60">
          Data: <a href="https://open-reaction-database.org/" target="_blank" rel="noopener" className="underline">Open Reaction Database</a> (CC-BY-SA 4.0)
          {" "}&middot;{" "}
          <a href="https://figshare.com/articles/dataset/Chemical_reactions_from_US_patents_1976-Sep2016_/5104873" target="_blank" rel="noopener" className="underline">USPTO/Lowe</a> (CC-0)
        </div>
      </footer>
    </div>
  );
}
