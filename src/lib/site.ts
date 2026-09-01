import index from "@/data/index.json";

export type Mode = "A_strict" | "A_loose" | "B_strict" | "B_loose";

export interface PlaySummary {
  id: string;
  ja: string;
  grc: string;
  author: string;
  genre: string;
  lines: number;
  sp: number;
  chi: Record<string, number>;
  vertices: number;
  scenes: { strict: number; loose: number };
}

export interface PlayDetail extends PlaySummary {
  urn: string;
  edition: { editor: string; title: string; date: string; ref: string };
  cast: Record<string, Record<string, string[]>>;
  edge_count: Record<string, number>;
  edges: Record<string, string[][]>;
  band: Record<string, { kind: "scene" | "chorus"; roles?: string[]; sp: number }[]>;
  boundaries: Record<string, number>;
  excess: Record<
    string,
    {
      chi: number;
      excess: number;
      k: number | null;
      union: string[];
      is_clique: boolean;
      host_scenes: number[];
      candidates: string[][];
      candidates_total: number;
    }
  >;
  control: Record<
    string,
    {
      observed: number;
      null_mean: number;
      null_min: number;
      null_max: number;
      p: number;
      trials: number;
      seed: number;
    }
  >;
  review_labels: string[];
}

export const PLAYS = index as PlaySummary[];

export const AUTHORS = ["アイスキュロス", "ソポクレス", "エウリピデス", "アリストパネス"];

/** 三人という数は上演の規約として外から持ち込む主張であり、χ の計算には使っていない。 */
export const CLAIMED_ACTORS = 3;

export function playsOf(author: string): PlaySummary[] {
  return PLAYS.filter((p) => p.author === author);
}

/** χ に応じた帯の色。三人までと、それを超えるものを分ける。 */
export function chiTone(chi: number): string {
  if (chi <= 2) return "var(--tone-2)";
  if (chi === CLAIMED_ACTORS) return "var(--tone-3)";
  if (chi === CLAIMED_ACTORS + 1) return "var(--tone-4)";
  return "var(--tone-many)";
}
