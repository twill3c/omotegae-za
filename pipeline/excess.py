"""L4 三人に収まらない役の特定(G-07′ (b))。

## 問い

χ ≥ 4 の篇について、「どの役を外せば三人で足りるか」を厳密に求める。

形式化すると **最小頂点削除問題**である —— G から頂点集合 S を取り除いたグラフが
k 彩色可能になるような、最小の |S| を求める。最小解が複数あるときは**全部返す**
(「この役か、あるいはこの役を外せばよい」という形で読めるようにする)。

## k = 3 をここに書くことについて(G-04 との関係)

`pipeline/coloring.py` と `web/lib/coloring.ts` には定数 3 を置かない。
χ そのものは「三で足りるか」を一切問わずに求める。**そこは循環してはならない。**

一方このファイルは、**求め終わった χ に対して外から立てる問い**を扱う。
「上演の規約が三人だったと言われている。では三に収まらないのはどれか」は
歴史的主張を明示的に持ち込む問いであり、隠れた仮定ではない。
そのため k は引数であり、既定値 3 の出所をここに書く。
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import coloring as C  # noqa: E402

# 古典期アテナイの上演で語る俳優は最大三人とされる。この数は**外から持ち込む主張**であり、
# χ の計算には一切使われていない(G-04)。
CLAIMED_ACTORS = 3


def minimal_deletions(verts: list[str], adj: list[int], k: int) -> tuple[int, list[list[str]]]:
    """G - S が k 彩色可能になる最小の S を全て返す。

    サイズ 0, 1, 2, … と昇順に全組合せを試すので、最初に見つかったサイズが最小である。
    """
    n = len(verts)
    for size in range(n + 1):
        found: list[list[str]] = []
        for combo in combinations(range(n), size):
            mask = 0
            for i in combo:
                mask |= 1 << i
            keep = [i for i in range(n) if not (mask >> i & 1)]
            remap = {v: j for j, v in enumerate(keep)}
            sub = []
            for v in keep:
                m = adj[v] & ~mask
                r = 0
                while m:
                    b = m & -m
                    r |= 1 << remap[b.bit_length() - 1]
                    m ^= b
                sub.append(r)
            if C.k_colorable(sub, k) is not None:
                found.append([verts[i] for i in combo])
        if found:
            return size, found
    raise AssertionError("到達しない")


def main() -> int:
    k = CLAIMED_ACTORS
    scenes_all = json.loads(
        (ROOT / "data" / "derived" / "scenes.json").read_text(encoding="utf-8")
    )
    coloring = json.loads(
        (ROOT / "data" / "derived" / "coloring.json").read_text(encoding="utf-8")
    )
    out: dict[str, dict] = {}

    for play, rec in sorted(scenes_all.items()):
        out[play] = {}
        for mode in ("A_strict", "A_loose"):
            chi = coloring[play][mode]["chi"]
            if chi <= k:
                out[play][mode] = {"chi": chi, "excess": 0, "candidates": []}
                continue
            verts, edges = C.build_graph(rec[mode]["scenes"])
            adj = C.adjacency(verts, edges)
            size, sets = minimal_deletions(verts, adj, k)
            union = sorted({x for s in sets for x in s})
            # 候補の和集合がクリークなら、超過は「その一群が互いに兼ねられない」ことに
            # 帰着する。どれを外しても同じなので、**特定の一役を「四人目」と呼んではならない**。
            is_clique = all(frozenset(pr) in edges for pr in combinations(union, 2))
            hosts = [
                i
                for i, s in enumerate(rec[mode]["scenes"])
                if set(union) <= set(s["roles"])
            ]
            out[play][mode] = {
                "chi": chi,
                "excess": size,
                "candidates": sorted(sets),
                "candidate_union": union,
                "union_is_clique": is_clique,
                "host_scenes": hosts,
                "k": k,
            }

    (ROOT / "data" / "derived" / "excess.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    TRAG = {"tlg0085", "tlg0011", "tlg0006"}
    print(f"=== 三人に収まらない役(k = {k})—— 緩 ===")
    print("悲劇:")
    for play, v in out.items():
        r = v["A_loose"]
        if play.split(".")[0] in TRAG and r["excess"]:
            alts = " / ".join("+".join(s) for s in r["candidates"])
            print(f"  {play}  χ={r['chi']}  最小 {r['excess']} 役:  {alts}")
    print("喜劇:")
    for play, v in out.items():
        r = v["A_loose"]
        if play.split(".")[0] not in TRAG and r["excess"]:
            n = len(r["candidates"])
            first = "+".join(r["candidates"][0])
            print(f"  {play}  χ={r['chi']}  最小 {r['excess']} 役:  {first}" + (f"  ほか {n - 1} 通り" if n > 1 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
