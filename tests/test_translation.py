"""L8 和訳の検査そのものを検査する。

**落ちない検査は検査ではない。** T-01〜T-05 のそれぞれについて、
わざと壊した訳文を作り、その検査が実際に発火することを確かめる(陽性対照)。
HC-070 に従い、対照の本体に「壊した箇所が実際に効く入力である」ことを書く。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import check_translation as CT  # noqa: E402

PLAY = "tlg0085.tlg002"


@pytest.fixture(scope="module")
def surface():
    s, probs = CT.load_names()
    assert not probs, probs
    assert s, "固有名の台帳が空 —— 検査が空回りしている"
    return s


@pytest.fixture
def tr_file(tmp_path, monkeypatch):
    """訳文ファイルを差し替えられるようにする。"""
    src = ROOT / "data" / "translation"
    work = tmp_path / "translation"
    work.mkdir()
    for p in src.glob("*.json"):
        (work / p.name).write_text(p.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(CT, "TR", work)
    return work / f"{PLAY}.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.mark.validation
def test_現状の訳は全検査を通る(surface):
    _row, problems = CT.check(PLAY, surface)
    assert not problems, problems


@pytest.mark.validation
def test_T01_原文に無い行番号を弾く(tr_file, surface):
    d = _load(tr_file)
    d["lines"]["99999"] = "ありえない行"
    _save(tr_file, d)
    _row, problems = CT.check(PLAY, surface)
    assert any(p.startswith("T-01") and "99999" in p for p in problems), problems


@pytest.mark.validation
def test_T01_空の訳文を弾く(tr_file, surface):
    d = _load(tr_file)
    d["lines"]["3"] = "   "
    _save(tr_file, d)
    _row, problems = CT.check(PLAY, surface)
    assert any(p.startswith("T-01") and "空" in p for p in problems), problems


@pytest.mark.validation
def test_T02_発話を半端に切ると落ちる(tr_file, surface):
    """1〜40 行は一つの発話。その途中を抜くと「半端」として発火するはず。

    **抜く行が発話の内側であること**を先に確かめる(HC-070)。
    """
    _lines, speeches = CT.greek_lines(PLAY)
    first = speeches[0]["lines"]
    assert "20" in first and first[0] != "20" and first[-1] != "20", first[:3]
    d = _load(tr_file)
    del d["lines"]["20"]
    _save(tr_file, d)
    _row, problems = CT.check(PLAY, surface)
    assert any(p.startswith("T-02") for p in problems), problems


@pytest.mark.validation
def test_T05_固有名を落とすと発火する(tr_file, surface):
    """5 行には Ξέρξης があり、台帳は「クセルクセス」を要求する。

    **その行が実際に固有名を含むこと**を先に確かめる。
    """
    lines, _sp = CT.greek_lines(PLAY)
    assert "Ξέρξης" in lines["5"], lines["5"]
    d = _load(tr_file)
    d["lines"]["5"] = "主君みずからが、"
    _save(tr_file, d)
    _row, problems = CT.check(PLAY, surface)
    assert any(p.startswith("T-05") and "クセルクセス" in p for p in problems), problems


@pytest.mark.validation
def test_T05_数詞を落とすと発火する(tr_file, surface):
    """47 行に δίρρυμα / τρίρρυμα(二頭立て・三頭立て)がある。"""
    lines, _sp = CT.greek_lines(PLAY)
    assert "τρίρρυμα" in lines["47"], lines["47"]
    d = _load(tr_file)
    d["lines"]["47"] = "隊列を、"
    _save(tr_file, d)
    _row, problems = CT.check(PLAY, surface)
    assert any(p.startswith("T-05") and "数詞" in p for p in problems), problems


@pytest.mark.validation
def test_数詞の判定は語中一致で誤発火しない(surface):
    """στρατιᾶς(軍勢)は「τρι(三)」を語中に含む。**語頭一致でなければ誤検出する。**

    9 行と 25 行に στρατι- があり、どちらの訳文にも数は無い。
    現行の訳が T-05 を通っていること自体がこの対照になっている。
    """
    lines, _sp = CT.greek_lines(PLAY)
    assert any("στρατι" in lines[n] for n in ("9", "25")), (lines["9"], lines["25"])
    _row, problems = CT.check(PLAY, surface)
    assert not [p for p in problems if "数詞" in p], problems


@pytest.mark.validation
def test_T04_同じカタカナに別語幹が当たると落ちる(tmp_path, monkeypatch):
    """カタカナは λ と ρ を潰す。衝突は homograph の明示を要求する。"""
    work = tmp_path / "translation"
    work.mkdir()
    (work / "names.json").write_text(
        json.dumps(
            {
                "_": [],
                "entries": [
                    {"stem": "Κλωθ", "ja": "クロト", "grc": ["Κλωθώ"]},
                    {"stem": "Κροτ", "ja": "クロト", "grc": ["Κρότων"]},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(CT, "TR", work)
    _s, problems = CT.load_names()
    assert any("衝突" in p for p in problems), problems


@pytest.mark.validation
def test_T04_homograph_を立てれば衝突は許される(tmp_path, monkeypatch):
    """対照の裏返し —— 明示すれば通る。通らなければ表が使えない。"""
    work = tmp_path / "translation"
    work.mkdir()
    (work / "names.json").write_text(
        json.dumps(
            {
                "_": [],
                "entries": [
                    {"stem": "Κλωθ", "ja": "クロト", "grc": ["Κλωθώ"], "homograph": True},
                    {"stem": "Κροτ", "ja": "クロト", "grc": ["Κρότων"], "homograph": True},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(CT, "TR", work)
    _s, problems = CT.load_names()
    assert not problems, problems


@pytest.mark.validation
def test_台帳の見出しは実際の原文に現れる(surface):
    """**死んだ見出しを作らない。** 表に書いた表層形が 45 篇のどこにも無ければ、
    それは確かめずに書いた形である(HC-120 の「表が実データから外れる」型)。
    """
    import re
    import xml.etree.ElementTree as ET

    NS = {"t": "http://www.tei-c.org/ns/1.0"}
    seen: set[str] = set()
    for p in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        root = ET.parse(p).getroot()
        for e in root.findall(".//t:l", NS):
            for w in re.findall(r"[Ͱ-Ͽἀ-῿ʼ']+", "".join(e.itertext())):
                seen.add(w.strip("'ʼ"))
    dead = sorted(set(surface) - seen)
    assert not dead, f"原文に現れない見出し: {dead}"
