import { useState, useRef, useCallback, useEffect } from "react";
import { ChevronUp, ChevronDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Reaction } from "@/types/reaction";
import {
  fetchReaction,
  fetchFirstReaction,
  fetchNextReaction,
  fetchPrevReaction,
  fetchReactionCount,
} from "@/services/api";
import { ReactionCard } from "./ReactionCard";

interface Props {
  isFavorite: (id: number) => boolean;
  onToggleFavorite: (id: number) => void;
  dark?: boolean;
}

function getIdFromUrl(): number | null {
  const params = new URLSearchParams(window.location.search);
  const id = params.get("id");
  return id ? Number(id) : null;
}

function setUrlId(id: number) {
  const url = new URL(window.location.href);
  url.searchParams.set("id", String(id));
  window.history.replaceState(null, "", url.toString());
}

export function SwipeContainer({ isFavorite, onToggleFavorite, dark }: Props) {
  const [current, setCurrent] = useState<Reaction | null>(null);
  const [prefetchedNext, setPrefetchedNext] = useState<Reaction | null>(null);
  const [animating, setAnimating] = useState<"up" | "down" | null>(null);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);

  const containerRef = useRef<HTMLDivElement>(null);
  const startY = useRef(0);
  const tracking = useRef(false);

  // Initial load — from URL param or first reaction
  useEffect(() => {
    (async () => {
      try {
        const [count, reaction] = await Promise.all([
          fetchReactionCount(),
          getIdFromUrl()
            ? fetchReaction(getIdFromUrl()!)
            : fetchFirstReaction(),
        ]);
        setTotal(count);
        setCurrent(reaction);
        setUrlId(reaction.id);
        setLoading(false);
      } catch (err) {
        console.error("Failed to load:", err);
      }
    })();
  }, []);

  // Prefetch next when current changes
  useEffect(() => {
    if (!current) return;
    setPrefetchedNext(null);
    fetchNextReaction(current.id).then(setPrefetchedNext).catch(console.error);
  }, [current]);

  const navigate = useCallback(
    async (direction: "up" | "down") => {
      if (animating || !current) return;
      setAnimating(direction);

      try {
        const next =
          direction === "up"
            ? prefetchedNext ?? (await fetchNextReaction(current.id))
            : await fetchPrevReaction(current.id);

        setTimeout(() => {
          setCurrent(next);
          setUrlId(next.id);
          setAnimating(null);
        }, 300);
      } catch (err) {
        console.error("Navigation failed:", err);
        setAnimating(null);
      }
    },
    [animating, current, prefetchedNext]
  );

  const goNext = useCallback(() => navigate("up"), [navigate]);
  const goPrev = useCallback(() => navigate("down"), [navigate]);

  // Touch events
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const onTouchStart = (e: TouchEvent) => {
      if (animating) return;
      startY.current = e.touches[0].clientY;
      tracking.current = true;
    };

    const onTouchMove = (e: TouchEvent) => {
      if (!tracking.current) return;
      e.preventDefault();
    };

    const onTouchEnd = (e: TouchEvent) => {
      if (!tracking.current) return;
      tracking.current = false;
      const dy = e.changedTouches[0].clientY - startY.current;
      if (dy < -40) goNext();
      else if (dy > 40) goPrev();
    };

    el.addEventListener("touchstart", onTouchStart, { passive: true });
    el.addEventListener("touchmove", onTouchMove, { passive: false });
    el.addEventListener("touchend", onTouchEnd, { passive: true });

    return () => {
      el.removeEventListener("touchstart", onTouchStart);
      el.removeEventListener("touchmove", onTouchMove);
      el.removeEventListener("touchend", onTouchEnd);
    };
  }, [animating, goNext, goPrev]);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "ArrowUp" || e.key === "ArrowLeft") goPrev();
      if (e.key === "ArrowDown" || e.key === "ArrowRight" || e.key === " ")
        goNext();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [goNext, goPrev]);

  if (loading || !current) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <p className="text-muted-foreground">Loading...</p>
      </div>
    );
  }

  const animClass =
    animating === "up"
      ? "animate-slide-up"
      : animating === "down"
        ? "animate-slide-down"
        : "";

  return (
    <div
      ref={containerRef}
      className="flex-1 flex flex-col items-center justify-center p-4 select-none overflow-hidden relative overscroll-none"
    >
      {/* Counter */}
      <div className="text-xs text-muted-foreground mb-2">
        #{current.id} of {total}
      </div>

      <div className={`w-full max-w-md ${animClass}`}>
        <ReactionCard
          key={current.id}
          reaction={current}
          isFavorite={isFavorite(current.id)}
          onToggleFavorite={() => onToggleFavorite(current.id)}
          dark={dark}
        />
      </div>

      {/* Navigation buttons */}
      <div className="absolute right-4 top-1/2 -translate-y-1/2 flex flex-col gap-2 hidden sm:flex">
        <Button
          variant="outline"
          size="icon"
          className="rounded-full w-10 h-10"
          disabled={!!animating}
          onClick={goPrev}
        >
          <ChevronUp className="w-5 h-5" />
        </Button>
        <Button
          variant="outline"
          size="icon"
          className="rounded-full w-10 h-10"
          disabled={!!animating}
          onClick={goNext}
        >
          <ChevronDown className="w-5 h-5" />
        </Button>
      </div>
    </div>
  );
}
