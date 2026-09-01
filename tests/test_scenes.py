"""L2 場面分割の不変量。"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

NS = {"t": "http://www.tei-c.org/ns/1.0"}
MODES = ["A_strict", "A_loose", "B_strict", "B_loose"]


@pytest.fixture(scope="module")
def scenes() -> dict:
    path = ROOT / "data" / "derived" / "scenes.json"
    if not path.exists():
        pytest.skip("先に pipeline/scenes.py を実行する")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ledger() -> list[dict]:
    return json.loads((ROOT / "data" / "derived" / "speakers.json").read_text(encoding="utf-8"))


@pytest.mark.validation
def test_消化率は全篇全読みで1000である(scenes):
    """G-02: すべての <sp> が場面か境界のどちらかに属し、二重計上も取りこぼしも無い。

    発話総数は TEI から数え直す(scenes.json の自己申告を信じない)。
    """
    for path in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        play = path.name.split(".perseus-")[0]
        total = len(ET.parse(path).getroot().findall(".//t:sp", NS))
        for mode in MODES:
            v = scenes[play][mode]
            consumed = sum(s["sp"] for s in v["scenes"]) + v["boundaries"]
            assert consumed == total, (play, mode, consumed, total)


@pytest.mark.validation
def test_空の場面を作らない(scenes):
    for play, v in scenes.items():
        for mode in MODES:
            for s in v[mode]["scenes"]:
                assert s["sp"] >= 1, (play, mode, s)


@pytest.mark.validation
def test_厳は緩より粗い(scenes):
    """厳は境界を減らすので、場面数は緩以下でなければならない。

    逆になっていたら、どちらかの分割器が壊れている。
    """
    for play, v in scenes.items():
        for r in ("A", "B"):
            assert len(v[f"{r}_strict"]["scenes"]) <= len(v[f"{r}_loose"]["scenes"]), play


@pytest.mark.validation
def test_厳の最大同席数は緩以上である(scenes):
    """厳は場面を併合するので役の集合は上位集合になり、最大同席数は減らない。

    **厳が反証側である**ことの機械的な表明でもある(SPEC §3.3)。
    """
    for play, v in scenes.items():
        for r in ("A", "B"):
            ms = max((len(s["roles"]) for s in v[f"{r}_strict"]["scenes"]), default=0)
            ml = max((len(s["roles"]) for s in v[f"{r}_loose"]["scenes"]), default=0)
            assert ms >= ml, (play, r, ms, ml)


@pytest.mark.validation
def test_場面の役に合唱隊が混ざらない(scenes, ledger):
    """合唱隊は俳優が演じないので、彩色の頂点になってはならない。

    読み B では Χορὸς Ἀγάθωνος と Δαναΐς を合唱隊に回すので、
    その 2 つが読み B の役に現れないことも同時に確かめる。
    """
    chorus = {(r["play"], r["label"]) for r in ledger if r["class"] == "chorus"}
    for play, v in scenes.items():
        for mode in MODES:
            for s in v[mode]["scenes"]:
                for role in s["roles"]:
                    assert (play, role) not in chorus, (play, mode, role)
    for mode in ("B_strict", "B_loose"):
        for s in scenes["tlg0019.tlg008"][mode]["scenes"]:
            assert "Χορὸς Ἀγάθωνος" not in s["roles"]
        for s in scenes["tlg0085.tlg001"][mode]["scenes"]:
            assert "Δαναΐς" not in s["roles"]


@pytest.mark.validation
def test_統合したラベルは場面の役に現れない(scenes, ledger):
    """表記事故 3 件は統合先に寄せる。元のラベルが役として残っていたら
    幽霊の頂点が 1 つ増える。"""
    merged = {(r["play"], r["label"]) for r in ledger if r["class"] == "merge"}
    for play, v in scenes.items():
        for mode in MODES:
            for s in v[mode]["scenes"]:
                for role in s["roles"]:
                    assert (play, role) not in merged, (play, mode, role)


@pytest.mark.validation
def test_読みBのコラは1頂点に潰れている(scenes):
    """SPEC §3.4: 読み B ではアカルナイの Κόρη を Κόρα に寄せる。"""
    for mode in ("B_strict", "B_loose"):
        for s in scenes["tlg0019.tlg001"][mode]["scenes"]:
            assert "Κόρη" not in s["roles"], s
    found = any(
        "Κόρα" in s["roles"] and "Κόρη" in s["roles"]
        for s in scenes["tlg0019.tlg001"]["A_loose"]["scenes"]
    )
    assert found, "読み A では 2 頂点として同席していなければ、読みの対比が成立しない"


@pytest.mark.validation
def test_境界に選ばれたdivは合唱歌の語彙が支配的である():
    """**非循環の検算。** 境界の判定に subtype の語彙は一切使っていない(L1 の話者分類だけ)。
    それでも選ばれた div が合唱歌の語彙に集中するなら、判定が合唱歌を拾えている証拠になる。

    実測 2026-09-02: 厳の境界 1,100 件超のうち strophe/antistrophe/epode/ephymn 系が
    大半を占めた。ここでは「合唱歌系が過半を占める」という緩い性質だけを検査する
    —— 比率を定数で固定すると、データが動いたときに正しい実装が落ちる(HC-016)。
    """
    import scenes as SC  # noqa: N813

    ledger = SC.load_ledger()
    from collections import Counter

    cuts: Counter = Counter()
    for path in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        play = path.name.split(".perseus-")[0]
        root = ET.parse(path).getroot()
        units = list(SC.speech_units(root, ledger, "A", play))
        _sc, _nb, c, _b = SC.segment(units, "strict")
        cuts += c

    sung = {
        "strophe", "antistrophe", "epode", "ephymn", "ephymn.", "ephymnion",
        "mesode", "lyric", "choral", "Choral", "Lyric-Scene", "monody", "kommos",
    }
    total = sum(cuts.values())
    hit = sum(v for k, v in cuts.items() if k in sung)
    assert total > 0
    assert hit / total > 0.5, (hit, total, cuts.most_common(10))
