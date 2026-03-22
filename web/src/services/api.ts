import type { Reaction } from "../types/reaction";

const API_BASE = "/api";

export async function fetchReaction(id: number): Promise<Reaction> {
  const res = await fetch(`${API_BASE}/reactions/${id}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchFirstReaction(): Promise<Reaction> {
  const res = await fetch(`${API_BASE}/reactions/first`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchNextReaction(currentId: number): Promise<Reaction> {
  const res = await fetch(`${API_BASE}/reactions/${currentId}/next`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchPrevReaction(currentId: number): Promise<Reaction> {
  const res = await fetch(`${API_BASE}/reactions/${currentId}/prev`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function fetchReactionCount(): Promise<number> {
  const res = await fetch(`${API_BASE}/reactions/count`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  const data = await res.json();
  return data.count;
}

export async function fetchRandomReaction(): Promise<Reaction> {
  const res = await fetch(`${API_BASE}/reactions/random`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
