"""L3 厳密彩色の不変量と、循環の禁止(G-04)の機械的検査。"""

from __future__ import annotations

import ast
import json
import re
import sys
from itertools import combinations
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import coloring as C  # noqa: E402

MODES = ["A_strict", "A_loose", "B_strict", "B_loose"]


@pytest.fixture(scope="module")
def result() -> dict:
    p = ROOT / "data" / "derived" / "coloring.json"
    if not p.exists():
        pytest.skip("先に pipeline/coloring.py を実行する")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def scenes() -> dict:
    return json.loads((ROOT / "data" / "derived" / "scenes.json").read_text(encoding="utf-8"))


@pytest.mark.validation
def test_配役は衝突を含まない(result, scenes):
    """出力された面替えスケジュールを場面から検算し直す。

    同じ場面に居合わせる二役が同一俳優に割り当てられていたら、その配役は上演できない。
    coloring.json の自己申告ではなく scenes.json から辺を作り直して確かめる。
    """
    for play, rec in result.items():
        for mode in MODES:
            who = {r: c for c, rs in rec[mode]["cast"].items() for r in rs}
            for s in scenes[play][mode]["scenes"]:
                for a, b in combinations(sorted(s["roles"]), 2):
                    assert who[a] != who[b], (play, mode, a, b)


@pytest.mark.validation
def test_配役の色数がχと一致する(result):
    for play, rec in result.items():
        for mode in MODES:
            assert len(rec[mode]["cast"]) == rec[mode]["chi"], (play, mode)


@pytest.mark.validation
def test_すべての役が一人の俳優に割り当てられている(result, scenes):
    for play, rec in result.items():
        for mode in MODES:
            roles = {r for s in scenes[play][mode]["scenes"] for r in s["roles"]}
            assigned = [r for rs in rec[mode]["cast"].values() for r in rs]
            assert sorted(assigned) == sorted(roles), (play, mode)
            assert len(assigned) == len(set(assigned)), (play, mode, "二重配役")


@pytest.mark.validation
def test_χはクリーク下限以上である(result):
    """場面はクリークを与えるので、最大場面の役数は χ の下限になる。"""
    for play, rec in result.items():
        for mode in MODES:
            assert rec[mode]["chi"] >= rec[mode]["clique_lower_bound"], (play, mode)


@pytest.mark.validation
def test_厳のχは緩以上である(result):
    """厳は場面を併合するので辺は増えるだけ。χ が減ることはない。

    **厳が反証側である**ことの機械的な表明(SPEC §3.3)。
    """
    for play, rec in result.items():
        for r in ("A", "B"):
            assert rec[f"{r}_strict"]["chi"] >= rec[f"{r}_loose"]["chi"], play


@pytest.mark.validation
def test_総当たりは悲劇を全数覆う(result):
    """目玉が関わるのは悲劇 34 篇。そこは近似でなく総当たりで裏づける。

    実測 2026-09-02: 悲劇 34 篇はすべて頂点数 12 以下で、総当たりが回った。
    """
    trag = [p for p in result if p.split(".")[0] in {"tlg0085", "tlg0011", "tlg0006"}]
    assert len(trag) == 34, len(trag)
    for play in trag:
        for mode in MODES:
            assert result[play][mode]["brute_forced"], (play, mode)


@pytest.mark.unit
def test_総当たりと後戻り探索が小さなグラフで一致する():
    """既知の答えを持つグラフで両方の実装を突き合わせる。

    期待値はグラフの構造から導出する(定数で書かない)。
    - 完全グラフ K_n の χ は n
    - 辺の無いグラフの χ は 1
    - 偶数長の閉路の χ は 2、奇数長は 3
    """
    def build(n, pairs):
        adj = [0] * n
        for a, b in pairs:
            adj[a] |= 1 << b
            adj[b] |= 1 << a
        return adj

    for n in range(1, 8):  # K_n
        adj = build(n, list(combinations(range(n), 2)))
        assert C.chromatic(adj, 1)[0] == n
        assert C.chromatic_bruteforce(adj) == n

    for n in range(2, 9):  # 空グラフ
        adj = build(n, [])
        assert C.chromatic(adj, 1)[0] == 1
        assert C.chromatic_bruteforce(adj) == 1

    for n in (4, 5, 6, 7, 8, 9):  # 閉路
        adj = build(n, [(i, (i + 1) % n) for i in range(n)])
        want = 2 if n % 2 == 0 else 3
        assert C.chromatic(adj, 1)[0] == want, n
        assert C.chromatic_bruteforce(adj) == want, n


@pytest.mark.validation
def test_G04_彩色の計算経路に定数3が現れない():
    """循環の禁止。「3 で足りるか」をコードに埋め込むと、答えを先に書いたことになる。

    Python は AST で数値リテラルを見る(コメント・文字列は対象外)。
    TypeScript は行コメントとブロックコメントを落としてから数字を見る。
    """
    py = ROOT / "pipeline" / "coloring.py"
    tree = ast.parse(py.read_text(encoding="utf-8"))
    hits = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, int) and n.value == 3
    ]
    assert not hits, f"{py} に整数リテラル 3 がある"

    ts = (ROOT / "src" / "lib" / "coloring.ts").read_text(encoding="utf-8")
    ts = re.sub(r"/\*.*?\*/", "", ts, flags=re.S)
    ts = re.sub(r"//.*", "", ts)
    assert not re.search(r"(?<![\w.])3(?![\w.])", ts), "coloring.ts に数値リテラル 3 がある"


@pytest.mark.validation
def test_読みの違いが影響する篇が特定されている(result):
    """SPEC §3.4: 決着しない 4 組について、読みで χ が動く篇を明示する。

    実測 2026-09-02: 動いたのは『女だけの祭』のみ(厳 8→7 / 緩 6→4)。
    アカルナイの Κόρα/Κόρη と嘆願する女たちの Δαναΐς は χ を動かさない。
    **論争が結論に影響しないことを示せるのは有用な結果である。**
    """
    moved = {
        play
        for play, rec in result.items()
        for m in ("strict", "loose")
        if rec[f"A_{m}"]["chi"] != rec[f"B_{m}"]["chi"]
    }
    assert moved == {"tlg0019.tlg008"}, moved
    assert result["tlg0019.tlg001"]["A_loose"]["chi"] == result["tlg0019.tlg001"]["B_loose"]["chi"]
    assert result["tlg0085.tlg001"]["A_loose"]["chi"] == result["tlg0085.tlg001"]["B_loose"]["chi"]
