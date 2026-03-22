export interface Reaction {
  id: number;
  reactants: string;
  conditions: string;
  product: string;
  named_reaction: string;
  category: string;
  difficulty: string;
  transform: string;
  notes: string;
  raw_conditions: string;
  source_row: string;
}

export interface ReactionsResponse {
  total: number;
  page: number;
  per_page: number;
  pages: number;
  reactions: Reaction[];
}
