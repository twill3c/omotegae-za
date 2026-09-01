"""L6 リーダーの不変量。

原文を「行番号のまま」読ませる以上、**一行も落とさない**ことと
**話者の並びが原文と一致する**ことが最低条件になる。
どちらも意味の判定を経由せずに機械的に確かめられる。
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import speakers as S  # noqa: E402

NS = {"t": "http://www.tei-c.org/ns/1.0"}
READER = ROOT / "src" / "data" / "reader"
OUT = ROOT / "out"


def _text(el) -> str:
    """本文。`<note>`(校訂者の注記)は本文ではないので数えない。

    パイプラインとは独立にここで実装する —— 同じ関数を呼んだのでは
    検査にならない。定義は SPEC と揃える(原文で落とすのは `<note>` だけ)。
    実測 2026-09-02: 注記だけで本文を持たない行が『追跡者たち』に存在する。
    """
    out: list[str] = []

    def walk(node, top=False):
        if not top and node.tag.split("}")[-1] == "note":
            if node.tail:
                out.append(node.tail)
            return
        if node.text:
            out.append(node.text)
        for ch in node:
            walk(ch)
        if not top and node.tail:
            out.append(node.tail)

    walk(el, top=True)
    return " ".join("".join(out).split())


@pytest.fixture(scope="module")
def report() -> dict:
    p = ROOT / "data" / "derived" / "reader_report.json"
    if not p.exists():
        pytest.skip("先に pipeline/build_reader.py を実行する")
    return json.loads(p.read_text(encoding="utf-8"))


@pytest.mark.validation
def test_本文のある行を一つも落とさない(report):
    """空行(実測 121 件)だけを落とし、それ以外は全部リーダーに載る。"""
    for path in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        play = path.name.split(".perseus-")[0]
        root = ET.parse(path).getroot()
        nonempty = [e for e in root.findall(".//t:l", NS) if _text(e)]
        data = json.loads((READER / f"{play}.json").read_text(encoding="utf-8"))
        kept = [ln for s in data["speeches"] for ln in s["lines"]]
        assert len(kept) == len(nonempty), (play, len(kept), len(nonempty))


@pytest.mark.validation
def test_話者の並びが原文と一致する():
    """**T-02 の前倒し。** リーダーの話者列を TEI から独立に作り直して突き合わせる。

    表記事故の統合(3 件)だけは反映されるので、統合先に読み替えてから比べる。
    """
    ledger = {
        (r["play"], r["label"]): r
        for r in json.loads((ROOT / "data" / "derived" / "speakers.json").read_text(encoding="utf-8"))
    }
    for path in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        play = path.name.split(".perseus-")[0]
        root = ET.parse(path).getroot()
        seq = []
        prev = None
        for sp in root.findall(".//t:sp", NS):
            lab = S.label_of(sp) or prev
            prev = lab
            rec = ledger.get((play, lab))
            if rec and rec["class"] == "merge":
                lab = rec["merge_into"]
            if any(_text(e) for e in sp.findall(".//t:l", NS)):
                seq.append(lab)
        data = json.loads((READER / f"{play}.json").read_text(encoding="utf-8"))
        assert [s["who"] for s in data["speeches"]] == seq, play


@pytest.mark.validation
def test_英訳は36篇である(report):
    """実測 2026-09-02。L0〜L5 で 39 / 41 と二度誤って報告した箇所を固定する。

    件数を定数で書く理由: この数は SPEC F-11 の記載そのものであり、
    ずれたら SPEC の側を直させたい。
    """
    with_en = [p for p, v in report.items() if v["en"]]
    assert len(with_en) == 36, len(with_en)
    arist = [p for p in with_en if p.startswith("tlg0019")]
    assert len(arist) == 2, arist
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    assert "45 篇中 36 篇" in spec


@pytest.mark.validation
def test_錨は原文の行番号にあるものだけを使う(report):
    """近い行へ寄せない。合わない錨は使わずに数える。"""
    for path in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        play = path.name.split(".perseus-")[0]
        data = json.loads((READER / f"{play}.json").read_text(encoding="utf-8"))
        if not data["en"]:
            continue
        root = ET.parse(path).getroot()
        gns = {e.get("n") for e in root.findall(".//t:l", NS) if _text(e)}
        for n in data["en"]["anchored"]:
            assert n in gns, (play, n)
        assert data["align"]["matched"] + data["align"]["unmatched"] == data["align"]["blocks"]


@pytest.mark.validation
def test_ソポクレスの錨不一致率が最も高い(report):
    """**校訂者交絡の予測が対応づけにも及ぶことの確認**(SPEC §2.1)。

    ソポクレスだけ原文(Storr)と英訳(Jebb)の校訂者が違う。
    アイスキュロスは原文も英訳も Smyth である。
    実測 2026-09-02: ソポクレス 2.2% に対し他は 0.6% 以下。
    ここでは順位(方向)だけを検査する —— 比率を定数で固定しない(HC-016)。
    """
    rate: dict[str, tuple[int, int]] = {}
    for play, v in report.items():
        if not v["en"]:
            continue
        g = play.split(".")[0]
        um, bl = rate.get(g, (0, 0))
        rate[g] = (um + v["unmatched"], bl + v["blocks"])
    ratios = {g: um / bl for g, (um, bl) in rate.items()}
    assert max(ratios, key=lambda g: ratios[g]) == "tlg0011", ratios


@pytest.mark.validation
def test_英訳が無い篇はその旨を画面に出す(report):
    if not (OUT / "index.html").exists():
        pytest.skip("先に next build を実行する")
    without = [p for p, v in report.items() if not v["en"]]
    assert len(without) == 9, without
    for play in without:
        html = (OUT / "play" / play / "read" / "index.html").read_text(encoding="utf-8")
        assert "英訳は Perseus に無い" in html, play


@pytest.mark.validation
def test_対応不能な錨の件数を画面に出す(report):
    """黙って落とさない。件数が画面に出ていること。"""
    if not (OUT / "index.html").exists():
        pytest.skip("先に next build を実行する")
    shown = 0
    for play, v in report.items():
        if not v["en"] or v["unmatched"] == 0:
            continue
        text = _visible(OUT / "play" / play / "read" / "index.html")
        assert f"{v['unmatched']} 件は原文の行番号に無い" in text, play
        shown += 1
    assert shown > 0


def _visible(html_path: Path) -> str:
    """見える本文だけを取り出す。

    React は隣り合うテキストノードの境目に `<!-- -->` を差し込むので、
    生の HTML では「2 件は…」が「2<!-- --> 件は…」になる。
    タグとコメントを落としてから照合する(L5 で同じ罠を踏んだ)。
    """
    html = html_path.read_text(encoding="utf-8")
    html = re.sub(r"<script\b.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", html))


@pytest.mark.validation
def test_継承した話者に印が付く():
    """原文に話者名が無い 3 件は、そう分かる形で出す(捏造しない)。"""
    if not (OUT / "index.html").exists():
        pytest.skip("先に next build を実行する")
    for play in ("tlg0011.tlg008", "tlg0085.tlg002", "tlg0085.tlg005"):
        data = json.loads((READER / f"{play}.json").read_text(encoding="utf-8"))
        assert sum(1 for s in data["speeches"] if s["inherited"]) == 1, play
        html = (OUT / "play" / play / "read" / "index.html").read_text(encoding="utf-8")
        assert "(継承)" in html, play
