/**
 * 衝突グラフの厳密彩色 —— TypeScript 実装(二実装照合の片側)。
 *
 * Python 側(pipeline/coloring.py)とは**問いの立て方から変える**。
 *
 *   Python : k を下限から 1 ずつ上げ、「k 彩色できるか」を DSATUR 順の後戻りで判定する
 *   ここ   : 制限増加列で集合分割を直接列挙し、色数を**最小化**する
 *
 * 同じ骨格を写すと、写した誤りも一緒に写る。定式化を変えることで、
 * 一方の探索順や枝刈りの誤りがもう一方に現れないようにする。
 *
 * G-04(循環の禁止): このファイルに定数 3 は現れない。
 * 「3 で足りるか」という問いをコードに埋め込まない。
 */

export interface Graph {
  vertices: string[];
  /** 無向辺。各要素は [頂点名, 頂点名]。 */
  edges: [string, string][];
}

export interface ColoringResult {
  chi: number;
  /** 色番号 → その色の俳優が担当する役(昇順)。 */
  cast: Record<string, string[]>;
}

/** 隣接をビットマスクで表す。頂点数は 32 を超えない前提(実測最大 23)。 */
function adjacency(g: Graph): number[] {
  const idx = new Map<string, number>();
  g.vertices.forEach((v, i) => idx.set(v, i));
  const adj = new Array<number>(g.vertices.length).fill(0);
  for (const [a, b] of g.edges) {
    const ia = idx.get(a);
    const ib = idx.get(b);
    if (ia === undefined || ib === undefined) {
      throw new Error(`辺の端点が頂点集合に無い: ${a} - ${b}`);
    }
    adj[ia] |= 1 << ib;
    adj[ib] |= 1 << ia;
  }
  return adj;
}

/** 貪欲に極大クリークを 1 つ取り、彩色数の下限を得る(枝刈り用)。 */
function cliqueLowerBound(adj: number[]): number {
  const n = adj.length;
  let best = n === 0 ? 0 : 1;
  for (let s = 0; s < n; s++) {
    let clique = 1 << s;
    let cand = adj[s];
    let size = 1;
    while (cand !== 0) {
      // 候補のうち次数が最大のものを取る
      let pick = -1;
      let pickDeg = -1;
      let m = cand;
      while (m !== 0) {
        const b = m & -m;
        const v = 31 - Math.clz32(b);
        const deg = popcount(adj[v] & cand);
        if (deg > pickDeg) {
          pickDeg = deg;
          pick = v;
        }
        m ^= b;
      }
      clique |= 1 << pick;
      size++;
      cand &= adj[pick];
    }
    if (size > best) best = size;
  }
  return best;
}

function popcount(x: number): number {
  let c = 0;
  let m = x;
  while (m !== 0) {
    m &= m - 1;
    c++;
  }
  return c;
}

/**
 * 集合分割を制限増加列で全列挙し、色数を最小化する。
 *
 * 制限増加列 a は a[0] = 0、a[i] <= max(a[0..i-1]) + 1 を満たす列で、
 * 集合分割の標準形と一対一に対応する。重複も取りこぼしも無い。
 * 現在の色数が既知の最良以上になった枝は打ち切る。
 */
export function chromatic(g: Graph): ColoringResult {
  const adj = adjacency(g);
  const n = adj.length;
  if (n === 0) return { chi: 0, cast: {} };

  // 頂点は次数の降順に並べ替えて探索する(Python 側の DSATUR とは別の順序)。
  const order = [...Array(n).keys()].sort((x, y) => {
    const d = popcount(adj[y]) - popcount(adj[x]);
    return d !== 0 ? d : g.vertices[x].localeCompare(g.vertices[y]);
  });
  const pos = new Array<number>(n);
  order.forEach((v, i) => (pos[v] = i));
  // 並べ替えた添字での隣接
  const a2 = order.map((v) => {
    let m = adj[v];
    let r = 0;
    while (m !== 0) {
      const b = m & -m;
      r |= 1 << pos[31 - Math.clz32(b)];
      m ^= b;
    }
    return r;
  });

  const lb = cliqueLowerBound(a2);
  const assign = new Array<number>(n).fill(-1);
  // n 色は必ず可能なので、初期値は n + 1 にする。n にすると χ = n の
  // グラフで最初の完全割り当てが `used >= best` に弾かれ、解が記録されない。
  let best = n + 1;
  let bestAssign: number[] = [];

  const rec = (i: number, used: number): void => {
    if (i === n) {
      if (used < best) {
        best = used;
        bestAssign = assign.slice();
      }
      return;
    }
    if (used >= best) return; // 部分割り当ての時点で既に最良以上 — 打ち切る
    for (let c = 0; c <= used; c++) {
      let ok = true;
      for (let j = 0; j < i; j++) {
        if (assign[j] === c && (a2[i] >> j) & 1) {
          ok = false;
          break;
        }
      }
      if (!ok) continue;
      assign[i] = c;
      rec(i + 1, Math.max(used, c + 1));
      assign[i] = -1;
      if (best === lb) return; // 下限に到達したら打ち切ってよい
    }
  };
  rec(0, 0);

  // 返す前に、得た割り当てが実際に正しいことを確かめる。
  for (let i = 0; i < n; i++) {
    let m = a2[i];
    while (m !== 0) {
      const b = m & -m;
      const j = 31 - Math.clz32(b);
      if (bestAssign[i] === bestAssign[j]) {
        throw new Error(`隣接頂点が同色: ${g.vertices[order[i]]} / ${g.vertices[order[j]]}`);
      }
      m ^= b;
    }
  }

  const cast: Record<string, string[]> = {};
  bestAssign.forEach((c, i) => {
    const key = String(c);
    (cast[key] ??= []).push(g.vertices[order[i]]);
  });
  for (const k of Object.keys(cast)) cast[k].sort();
  return { chi: best, cast };
}
