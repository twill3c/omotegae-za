"""L3 衝突グラフの厳密彩色 — 何人の俳優で上演できるか。

## グラフ

- 頂点 = 語る役(合唱隊を除く。L1 の分類による)
- 辺 = 同じ場面に居合わせる二役(同一俳優が兼ねられない)

各場面はその場面の役の**クリーク**を与える。したがって「最大の場面の役数」は
χ の下限になる(クリーク数 ≤ χ)。

## 厳密性

貪欲彩色・近似は最終値にしない(SPEC F-04)。k = 下限から 1 ずつ上げ、
k-彩色可能性を DSATUR 順の後戻り探索で判定する。最初に通った k が χ である。

**G-04(循環の禁止): このファイルに定数 3 は現れない。** k は下限から始めて
上限(頂点数)まで動く。「3 で足りるか」という問いをコードに埋め込まない。

## 第三のオラクル

頂点数 12 以下の篇では、**集合分割の総当たり**(制限増加列による標準形の全列挙)で
χ を独立に求め、後戻り探索の結果と突き合わせる。実測 2026-09-02 で 45 篇中 38 篇が
該当し、**悲劇 34 篇はすべて含まれる**。目玉が関わる篇は全数が総当たりで裏づけられる。
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DERIVED = ROOT / "data" / "derived"

BRUTE_MAX = 12  # 総当たりを回す頂点数の上限(Bell(12) = 4,213,597)


def build_graph(scenes: list[dict]) -> tuple[list[str], set[frozenset[str]]]:
    verts = sorted({r for s in scenes for r in s["roles"]})
    edges: set[frozenset[str]] = set()
    for s in scenes:
        for a, b in combinations(sorted(s["roles"]), 2):
            edges.add(frozenset((a, b)))
    return verts, edges


def adjacency(verts: list[str], edges: set[frozenset[str]]) -> list[int]:
    """頂点をビットマスクの隣接集合で表す。"""
    idx = {v: i for i, v in enumerate(verts)}
    adj = [0] * len(verts)
    for e in edges:
        a, b = sorted(e)
        adj[idx[a]] |= 1 << idx[b]
        adj[idx[b]] |= 1 << idx[a]
    return adj


def k_colorable(adj: list[int], k: int) -> list[int] | None:
    """k 彩色が可能なら色割り当てを返す。DSATUR 順の後戻り探索。"""
    n = len(adj)
    if n == 0:
        return []
    color = [-1] * n
    # 各頂点で使用済みの色のビットマスク
    used = [0] * n

    def pick() -> int:
        """彩度(隣接する異なり色数)が最大、同値なら次数が最大の未彩色頂点。"""
        best, best_key = -1, None
        for v in range(n):
            if color[v] != -1:
                continue
            key = (bin(used[v]).count("1"), bin(adj[v]).count("1"))
            if best_key is None or key > best_key:
                best, best_key = v, key
        return best

    def rec(assigned: int) -> bool:
        if assigned == n:
            return True
        v = pick()
        # 対称性の除去: まだどこにも使われていない色は 1 つだけ試す
        max_used = max(color) if assigned else -1
        limit = min(k - 1, max_used + 1)
        for c in range(limit + 1):
            if used[v] >> c & 1:
                continue
            color[v] = c
            touched = []
            m = adj[v]
            while m:
                b = m & -m
                u = b.bit_length() - 1
                if not (used[u] >> c & 1):
                    used[u] |= 1 << c
                    touched.append(u)
                m ^= b
            if rec(assigned + 1):
                return True
            for u in touched:
                used[u] &= ~(1 << c)
            color[v] = -1
        return False

    return color[:] if rec(0) else None


def chromatic(adj: list[int], lower: int) -> tuple[int, list[int]]:
    """厳密な彩色数と、その色割り当て。k を下限から 1 ずつ上げる。"""
    n = len(adj)
    if n == 0:
        return 0, []
    k = max(1, lower)
    while k <= n:
        got = k_colorable(adj, k)
        if got is not None:
            return k, got
        k += 1
    raise AssertionError("頂点数を超えても彩色できない — 実装の誤り")


def chromatic_bruteforce(adj: list[int]) -> int:
    """集合分割の全列挙による厳密な彩色数(頂点数 12 以下でのみ使う)。

    制限増加列(a[0]=0, a[i] <= max(a[:i])+1)は集合分割の標準形と一対一に対応する。
    重複も取りこぼしもなく全分割を一度ずつ数える。
    """
    n = len(adj)
    if n == 0:
        return 0
    best = n
    a = [0] * n

    def rec(i: int, used: int) -> None:
        nonlocal best
        if used >= best:          # 既に最良以上の色数 — この先は改善しない
            return
        if i == n:
            best = used
            return
        for c in range(used + 1):
            ok = True
            for j in range(i):
                if a[j] == c and (adj[i] >> j & 1):
                    ok = False
                    break
            if ok:
                a[i] = c
                rec(i + 1, max(used, c + 1))
        a[i] = -1

    rec(0, 0)
    return best


def verify(adj: list[int], color: list[int]) -> None:
    """返された色割り当てが実際に正しいことを確かめる。"""
    for v, m in enumerate(adj):
        mm = m
        while mm:
            b = mm & -mm
            u = b.bit_length() - 1
            assert color[v] != color[u], f"隣接頂点 {v},{u} が同色 {color[v]}"
            mm ^= b


def main() -> int:
    scenes_all = json.loads((DERIVED / "scenes.json").read_text(encoding="utf-8"))
    out: dict[str, dict] = {}
    graphs: dict[str, dict] = {}
    brute_checked = 0

    for play, rec in sorted(scenes_all.items()):
        out[play] = {}
        graphs[play] = {}
        for mode in ("A_strict", "A_loose", "B_strict", "B_loose"):
            scenes = rec[mode]["scenes"]
            verts, edges = build_graph(scenes)
            adj = adjacency(verts, edges)
            lower = max((len(s["roles"]) for s in scenes), default=0)

            chi, color = chromatic(adj, lower)
            verify(adj, color)
            assert chi >= lower, (play, mode, chi, lower)

            if len(verts) <= BRUTE_MAX:
                chi_b = chromatic_bruteforce(adj)
                assert chi_b == chi, f"{play} {mode}: 総当たり {chi_b} != 探索 {chi}"
                brute_checked += 1

            # 面替えスケジュール: 俳優ごとに担当する役
            cast: dict[int, list[str]] = {}
            for v, c in zip(verts, color):
                cast.setdefault(c, []).append(v)

            out[play][mode] = {
                "chi": chi,
                "vertices": len(verts),
                "edges": len(edges),
                "clique_lower_bound": lower,
                "brute_forced": len(verts) <= BRUTE_MAX,
                "cast": {str(k): sorted(v) for k, v in sorted(cast.items())},
            }
            graphs[play][mode] = {
                "vertices": verts,
                "edges": sorted(sorted(e) for e in edges),
                "clique_lower_bound": lower,
            }

    (DERIVED / "coloring.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (DERIVED / "graphs.json").write_text(
        json.dumps(graphs, ensure_ascii=False), encoding="utf-8"
    )

    print(f"総当たりで裏づけた組: {brute_checked} / {len(out) * 4}")
    print(f"\n{'篇':<16}{'厳A':>5}{'緩A':>5}{'厳B':>5}{'緩B':>5}{'頂点':>5}  総当たり")
    for play, v in out.items():
        print(
            f"{play:<16}{v['A_strict']['chi']:>5}{v['A_loose']['chi']:>5}"
            f"{v['B_strict']['chi']:>5}{v['B_loose']['chi']:>5}"
            f"{v['A_strict']['vertices']:>5}  {'○' if v['A_strict']['brute_forced'] else '—'}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
