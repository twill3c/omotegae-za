"""L4 置換対照の不変量(G-05)。

対照そのものが正しく壊れているかを確かめる。**帰無分布が実測と同じものを
返してしまう対照は、何も検定していない。**
"""

from __future__ import annotations

import json
import random
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import control as CTL  # noqa: E402
import scenes as SC  # noqa: E402

NS = {"t": "http://www.tei-c.org/ns/1.0"}
TRAG = {"tlg0085", "tlg0011", "tlg0006"}


@pytest.fixture(scope="module")
def control() -> dict:
    p = ROOT / "data" / "derived" / "control.json"
    if not p.exists():
        pytest.skip("先に pipeline/control.py を実行する")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.validation
def test_置換は保つべきものを保つ():
    """陽性対照の裏返し —— **置換が壊してはいけないものを壊していないか。**

    置換で保たれるべきもの: 場面の数、場面ごとの発話数、異なり役数、
    各役の発話回数の多重集合。これらが動いていたら、有意差は役の配置ではなく
    別のものを測っている。

    実測 2026-09-02: アンティゴネ(役 9)で 30 回の置換すべてが不変量を保った。
    """
    play = "tlg0011.tlg002"
    ledger = SC.load_ledger()
    root = ET.parse(ROOT / "data" / "raw" / f"{play}.perseus-grc2.xml").getroot()
    units = list(SC.speech_units(root, ledger, "A", play))
    base, _nb, _c = SC.segment(units, "loose")
    base_sizes = [s["sp"] for s in base]
    base_roles = {r for s in base for r in s["roles"]}
    base_counts = Counter(
        next(iter(roles)) for cls, roles, _d, _s in units if cls == "actor" and len(roles) == 1
    )

    rng = random.Random(1)
    for _ in range(30):
        perm = CTL.permuted_scenes(units, "loose", rng)
        assert [s["sp"] for s in perm] == base_sizes
        assert {r for s in perm for r in s["roles"]} == base_roles


@pytest.mark.validation
def test_対照が無情報になる組は把握されている():
    """**対照が何も言えないのはどういうときか。**

    最初この検査を「帰無分布が一点なら無情報」と書いたが、**誤りだった**。
    ソポクレス『エレクトラ』とアイスキュロス『縛られたプロメテウス』は
    帰無が常に 6(一点)で実測 3、p = 0.0005 —— 一点の帰無は無情報どころか
    最強の証拠になりうる。

    無情報の条件は `null_min >= observed`(帰無が実測を下回れない)**でもない**。
    それは**強く有意な組にも当てはまる** —— 帰無が常に実測より大きいのは
    最も強い証拠である。二度間違えた。

    無情報とは端的に **p が大きい**こと、すなわち帰無がしばしば実測に並ぶことである。
    実測 2026-09-02 で p >= 0.5 になるのは 5 組だけで、いずれも理由が説明できる:
    キュクロプス厳緩(役 3)・追跡者たち厳(断片)・福の神厳(全役が一場面)・
    エウメニデス緩(§3.3 の弱点)。
    """
    ctl = json.loads((ROOT / "data" / "derived" / "control.json").read_text(encoding="utf-8"))
    blind = {
        (p, m)
        for p, v in ctl.items()
        for m in ("strict", "loose")
        if v[m]["p"] >= 0.5
    }
    assert blind == {
        ("tlg0006.tlg001", "strict"),
        ("tlg0006.tlg001", "loose"),
        ("tlg0011.tlg008", "strict"),
        ("tlg0019.tlg011", "strict"),
        ("tlg0085.tlg007", "loose"),
    }, blind


@pytest.mark.validation
def test_一点の帰無でも実測を上回れば有意になる():
    """上の誤りを二度としないための表明。

    帰無が一点でも、その値が実測より大きければ p は最小値を取る。
    """
    ctl = json.loads((ROOT / "data" / "derived" / "control.json").read_text(encoding="utf-8"))
    for play in ("tlg0011.tlg005", "tlg0085.tlg003"):
        v = ctl[play]["loose"]
        assert v["null_min"] == v["null_max"] > v["observed"]
        assert v["p"] == pytest.approx(1 / (CTL.TRIALS + 1), rel=1e-3)


@pytest.mark.validation
def test_実測は帰無の範囲に収まる(control):
    """実測 χ が帰無分布の範囲外にあるのは異常ではないが、**下回る**のは正常、
    **上回る**のは方法の弱点の徴候である。上回った篇は必ず把握されていること。"""
    over = {
        (p, m)
        for p, v in control.items()
        for m in ("strict", "loose")
        if v[m]["observed"] > v[m]["null_mean"]
    }
    assert over == {("tlg0085.tlg007", "loose")}, over


@pytest.mark.validation
def test_G05_悲劇の大半で有意である(control):
    """SPEC G-05。閾値の 0.01 は SPEC の条項そのもの。

    篇数は定数で固定しない —— データが動けば動く。「大半」という性質を
    比率で書き、実測値はコメントに残す(HC-016)。
    実測 2026-09-02: 厳 30/34・緩 29/34。
    """
    trag = [p for p in control if p.split(".")[0] in TRAG]
    for mode in ("strict", "loose"):
        sig = sum(1 for p in trag if control[p][mode]["p"] < 0.01)
        assert sig / len(trag) > 0.8, (mode, sig, len(trag))


@pytest.mark.validation
def test_対照の設定が記録されている(control):
    """seed と試行回数が出力に残っていなければ、この検定は再現できない。"""
    for p, v in control.items():
        for m in ("strict", "loose"):
            assert v[m]["seed"] == CTL.SEED
            assert v[m]["trials"] == CTL.TRIALS
            assert 0 < v[m]["p"] <= 1.0


@pytest.mark.validation
def test_p値は補正された片側検定である(control):
    """(k+1)/(N+1) の補正により p = 0 は出ない。最小値は 1/(N+1)。"""
    lo = min(v[m]["p"] for v in control.values() for m in ("strict", "loose"))
    assert lo == pytest.approx(1 / (CTL.TRIALS + 1), rel=1e-3), lo
