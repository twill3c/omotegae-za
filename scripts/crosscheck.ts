/**
 * 二実装照合(G-03)—— Python が出した χ と TypeScript が出した χ を全数で突き合わせる。
 *
 *   node --experimental-strip-types web/lib/crosscheck.ts
 *
 * 不一致が 1 件でもあれば非ゼロで終了する。
 */

import { readFileSync } from "node:fs";
import { chromatic, type Graph } from "../src/lib/coloring.ts";

const DERIVED = new URL("../data/derived/", import.meta.url);

type GraphFile = Record<string, Record<string, { vertices: string[]; edges: string[][] }>>;
type ColorFile = Record<string, Record<string, { chi: number; vertices: number }>>;

const graphs: GraphFile = JSON.parse(readFileSync(new URL("graphs.json", DERIVED), "utf-8"));
const python: ColorFile = JSON.parse(readFileSync(new URL("coloring.json", DERIVED), "utf-8"));

const plays = Object.keys(graphs).sort();
const modes = ["A_strict", "A_loose", "B_strict", "B_loose"];

let checked = 0;
const mismatches: string[] = [];

for (const play of plays) {
  for (const mode of modes) {
    const src = graphs[play]?.[mode];
    const py = python[play]?.[mode];
    if (!src || !py) {
      mismatches.push(`${play} ${mode}: 片側に無い`);
      continue;
    }
    const g: Graph = {
      vertices: src.vertices,
      edges: src.edges.map((e) => [e[0], e[1]] as [string, string]),
    };
    const ts = chromatic(g);
    checked++;
    if (ts.chi !== py.chi) {
      mismatches.push(`${play} ${mode}: TS ${ts.chi} != Py ${py.chi}`);
    }
    if (g.vertices.length !== py.vertices) {
      mismatches.push(`${play} ${mode}: 頂点数 TS ${g.vertices.length} != Py ${py.vertices}`);
    }
  }
}

console.log(`照合: ${checked} 組(${plays.length} 篇 × ${modes.length} 通り)`);
if (mismatches.length > 0) {
  console.error(`不一致 ${mismatches.length} 件:`);
  for (const m of mismatches) console.error("  " + m);
  process.exit(1);
}
console.log("不一致 0 件 — G-03 通過");
