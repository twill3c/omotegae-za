"""L4 超過役の特定(F-14 / G-07′ (b))の不変量。

**特定の一役を「四人目」と呼んではならない。** 最適彩色は複数あり、
どの役に単独の色が付くかは恣意的である。不変なのは
「取り除けば k 彩色になる最小の役集合」であって、彩色の中身ではない。
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import coloring as C  # noqa: E402

TRAG = {"tlg0085", "tlg0011", "tlg0006"}


@pytest.fixture(scope="module")
def excess() -> dict:
    p = ROOT / "data" / "derived" / "excess.json"
    if not p.exists():
        pytest.skip("先に pipeline/excess.py を実行する")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def scenes() -> dict:
    return json.loads((ROOT / "data" / "derived" / "scenes.json").read_text(encoding="utf-8"))


@pytest.mark.validation
def test_候補を外せば本当にk彩色になる(excess, scenes):
    """出力を鵜呑みにせず、場面から作り直したグラフで実際に削って確かめる。"""
    for play, rec in excess.items():
        for mode in ("A_strict", "A_loose"):
            r = rec[mode]
            if not r["excess"]:
                continue
            verts, edges = C.build_graph(scenes[play][mode]["scenes"])
            for cand in r["candidates"]:
                keep = [v for v in verts if v not in cand]
                sub = [
                    {"roles": [x for x in s["roles"] if x in keep], "sp": s["sp"]}
                    for s in scenes[play][mode]["scenes"]
                ]
                v2, e2 = C.build_graph(sub)
                adj = C.adjacency(v2, e2)
                assert C.k_colorable(adj, r["k"]) is not None, (play, mode, cand)


@pytest.mark.validation
def test_一つ少なく削っては足りない(excess, scenes):
    """最小性の検査。**より小さい削除で足りるなら、それは最小解ではない。**

    候補の 1 つから 1 役だけ戻して k 彩色できないことを確かめる。
    (全組合せの再探索は重いので、返された解の近傍で最小性を突く。)
    """
    for play, rec in excess.items():
        for mode in ("A_strict", "A_loose"):
            r = rec[mode]
            if r["excess"] < 1:
                continue
            cand = r["candidates"][0]
            verts, edges = C.build_graph(scenes[play][mode]["scenes"])
            for back in cand:
                smaller = [x for x in cand if x != back]
                keep = [v for v in verts if v not in smaller]
                sub = [
                    {"roles": [x for x in s["roles"] if x in keep], "sp": s["sp"]}
                    for s in scenes[play][mode]["scenes"]
                ]
                v2, e2 = C.build_graph(sub)
                adj = C.adjacency(v2, e2)
                assert C.k_colorable(adj, r["k"]) is None, (play, mode, smaller)


@pytest.mark.validation
def test_χがk以下の篇は超過0である(excess):
    for play, rec in excess.items():
        for mode in ("A_strict", "A_loose"):
            r = rec[mode]
            if r["chi"] <= 3:
                assert r["excess"] == 0 and r["candidates"] == [], (play, mode)


@pytest.mark.validation
def test_χ4の悲劇は最小1役かつ候補がクリークを成す(excess):
    """実測 2026-09-02(緩): χ = 4 の悲劇 6 篇はすべて最小 1 役・候補 4 通りで、
    その 4 役はクリークを成す。**どれを外しても等しく解消するので、
    特定の一役を四人目と名指しできない**(SPEC §3.5 の訂正)。

    篇の並びは定数で固定しない。「χ = 4 の悲劇なら必ずこの形」という性質で書く。
    """
    seen = 0
    for play, rec in excess.items():
        if play.split(".")[0] not in TRAG:
            continue
        r = rec["A_loose"]
        if r["chi"] != 4:
            continue
        seen += 1
        assert r["excess"] == 1, (play, r["excess"])
        assert r["union_is_clique"], play
        assert len(r["candidates"]) == len(r["candidate_union"]), play
        assert len(r["candidate_union"]) == r["chi"], (play, r["candidate_union"])
    assert seen > 0, "χ = 4 の悲劇が 1 篇も無い — 検査が空回りしている"


@pytest.mark.validation
def test_候補の和集合は本当にクリークである(excess, scenes):
    """union_is_clique の自己申告を場面から検算し直す。"""
    for play, rec in excess.items():
        for mode in ("A_strict", "A_loose"):
            r = rec[mode]
            if not r["excess"]:
                continue
            _v, edges = C.build_graph(scenes[play][mode]["scenes"])
            actual = all(
                frozenset(pr) in edges for pr in combinations(r["candidate_union"], 2)
            )
            assert actual == r["union_is_clique"], (play, mode)


@pytest.mark.validation
def test_エウメニデスの四役はプロロゴスに現れる(excess, scenes):
    """SPEC §3.3 の弱点と §3.5 の結果が同じ箇所を指していることの表明。

    合唱隊が語らない区間で退場を検出できない ⇒ プロロゴスが一場面に併合される。
    エウメニデスの超過はまさにその第 0 場面で生じている。
    """
    r = excess["tlg0085.tlg007"]["A_loose"]
    assert r["chi"] == 4
    assert 0 in r["host_scenes"], r["host_scenes"]
