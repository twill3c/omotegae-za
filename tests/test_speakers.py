"""L1 話者名台帳の不変量。

期待値は件数の定数ではなく「集合が一致する」「取りこぼしが無い」で書く(HC-016)。
定数で書かざるをえないものには実測日を添える。
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

import speakers as S  # noqa: E402

NS = {"t": "http://www.tei-c.org/ns/1.0"}


@pytest.fixture(scope="module")
def ledger() -> list[dict]:
    path = ROOT / "data" / "derived" / "speakers.json"
    if not path.exists():
        pytest.skip("data/derived/speakers.json が無い。先に pipeline/speakers.py を実行する")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def raw_labels() -> dict[str, set[str]]:
    """TEI から直接読み直した (篇 → ラベル集合)。台帳とは独立の経路で作る。"""
    out: dict[str, set[str]] = {}
    for path in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        stem = path.name.split(".perseus-")[0]
        root = ET.parse(path).getroot()
        labs: set[str] = set()
        prev = None
        for sp in root.findall(".//t:sp", NS):
            lab = S.label_of(sp)
            if lab is None:
                lab = prev  # 話者欠落は直前を継承(SPEC §2.2 ③)
            prev = lab
            labs.add(lab)
        out[stem] = labs
    return out


@pytest.mark.validation
def test_台帳は実データのラベルを取りこぼさない(ledger, raw_labels):
    """台帳の (篇, ラベル) 集合が、TEI から読み直した集合と完全に一致する。

    件数ではなく集合で比べる。データが動けば集合も動くが、
    「取りこぼしが無い」という性質は動かない。
    """
    from_ledger = {(r["play"], r["label"]) for r in ledger}
    from_raw = {(p, lab) for p, labs in raw_labels.items() for lab in labs}
    assert from_ledger == from_raw


@pytest.mark.validation
def test_すべてのラベルに分類と根拠がある(ledger):
    for r in ledger:
        assert r["class"] in {"actor", "chorus", "joint", "merge", "review"}, r
        assert r["reason"].strip(), r


@pytest.mark.validation
def test_統合先は同じ篇に実在する(ledger):
    per_play: dict[str, set[str]] = {}
    for r in ledger:
        per_play.setdefault(r["play"], set()).add(r["label"])
    for r in ledger:
        if r["class"] == "merge":
            assert r["merge_into"] in per_play[r["play"]], r


@pytest.mark.validation
def test_共同発話の構成員は同じ篇に単独ラベルを持つ(ledger):
    """分解先が実在しなければ、分解は頂点を捏造することになる。"""
    per_play: dict[str, set[str]] = {}
    for r in ledger:
        per_play.setdefault(r["play"], set()).add(r["label"])
    for r in ledger:
        if r["class"] == "joint":
            assert len(r["members"]) >= 2, r
            for m in r["members"]:
                assert m in per_play[r["play"]], (r, m)


@pytest.mark.validation
def test_合唱隊語幹を持つラベルは合唱隊かreviewである(ledger):
    """χορ/ἡμιχορ を含むラベルを actor に落とすと、合唱隊が俳優として数えられる。

    語幹判定はここでのみ使う「取りこぼし検出器」であって、分類そのものは
    pipeline/speakers.py の手書き表が行う(SPEC F-02: 自動正規化はしない)。
    """
    def stem(s: str) -> str:
        return "".join(
            c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)
        ).lower()

    bad = [r for r in ledger if "χορ" in stem(r["label"]) and r["class"] not in {"chorus", "review"}]
    assert not bad, bad


@pytest.mark.validation
def test_合唱隊に分類したものは合唱隊語幹を持つ(ledger):
    """逆向きの検査。語幹を持たないものを合唱隊にしていたら根拠を疑う。"""
    def stem(s: str) -> str:
        return "".join(
            c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c)
        ).lower()

    bad = [r for r in ledger if r["class"] == "chorus" and "χορ" not in stem(r["label"])]
    assert not bad, bad


@pytest.mark.validation
def test_話者欠落の継承は実測した3件だけである():
    """実測 2026-09-02: <speaker> を持たない <sp> は 3 件(SPEC §2.2 ③)。

    定数で書く理由: この 3 件は個別に目視して継承の妥当性を確認した対象そのものであり、
    件数が増えたら「まだ目視していない継承」が発生したことを意味する。
    増減したらテストが落ちて、目視のやり直しを促すのが正しい。
    """
    total = 0
    where = []
    for path in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        root = ET.parse(path).getroot()
        n = sum(1 for sp in root.findall(".//t:sp", NS) if S.label_of(sp) is None)
        if n:
            where.append((path.name.split(".perseus-")[0], n))
        total += n
    assert total == 3, where
    assert dict(where) == {
        "tlg0011.tlg008": 1,
        "tlg0085.tlg002": 1,
        "tlg0085.tlg005": 1,
    }, where


@pytest.mark.validation
def test_review_はすべて_SPEC_に列挙されている(ledger):
    """決着しないものを台帳に置いたまま SPEC に書かないと、黙って消える(G-01)。"""
    spec = (ROOT / "SPEC.md").read_text(encoding="utf-8")
    for r in ledger:
        if r["class"] == "review":
            assert r["label"] in spec, f"{r['play']} {r['label']} が SPEC §3.4 に無い"


@pytest.mark.validation
def test_採否表に死んだ項目が無い():
    """表が実データから外れていないか。speakers.main() 内の検算と同じ性質を、
    パイプラインを走らせずに確かめる(HC-120)。"""
    seen: set[tuple[str, str]] = set()
    for path in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        stem = path.name.split(".perseus-")[0]
        root = ET.parse(path).getroot()
        prev = None
        for sp in root.findall(".//t:sp", NS):
            lab = S.label_of(sp) or prev
            prev = lab
            seen.add((stem, lab))
    table = set(S.CHORUS) | set(S.MERGE) | set(S.JOINT) | set(S.REVIEW)
    assert not (table - seen), sorted(table - seen)


@pytest.mark.validation
def test_数値部を持たない行番号は補正表に載っているものだけである():
    """G-02(c): 補正表に載っていない外れ値を 0 にする。

    数値部が取れない `n` があると G-02 の単調性検査が成立しない。実測 2026-09-02 で
    『福の神』に 2 件(`3933` `NaN`)。どちらも前後の行番号から補正先が決まる。
    **新しい外れ値が現れたらテストが落ち、人が一件ずつ判断することを強制する。**
    """
    corr = json.loads((ROOT / "data" / "corrections.json").read_text(encoding="utf-8"))
    known = {(c["play"], c["observed"]) for c in corr["line_numbers"]}
    bad = []
    for path in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        stem = path.name.split(".perseus-")[0]
        root = ET.parse(path).getroot()
        for el in root.findall(".//t:l", NS):
            n = el.get("n")
            if not re.match(r"^\d+", n or "") and (stem, n) not in known:
                bad.append((stem, n))
    assert not bad, bad[:10]


@pytest.mark.validation
def test_補正表に死んだ項目が無い():
    """補正済みの誤植が上流で直れば、表の項目は実データから消える。
    そのとき表を残したままにすると、次の外れ値を見逃す穴になる。"""
    corr = json.loads((ROOT / "data" / "corrections.json").read_text(encoding="utf-8"))
    stale = []
    for c in corr["line_numbers"]:
        path = ROOT / "data" / "raw" / f"{c['play']}.perseus-grc2.xml"
        root = ET.parse(path).getroot()
        if c["observed"] not in {el.get("n") for el in root.findall(".//t:l", NS)}:
            stale.append(c)
    assert not stale, stale


@pytest.mark.validation
def test_補正先は同じ篇の行番号と衝突しない():
    """補正先がすでに使われていたら、補正が別の行を潰す。"""
    corr = json.loads((ROOT / "data" / "corrections.json").read_text(encoding="utf-8"))
    clash = []
    for c in corr["line_numbers"]:
        path = ROOT / "data" / "raw" / f"{c['play']}.perseus-grc2.xml"
        root = ET.parse(path).getroot()
        if c["corrected"] in {el.get("n") for el in root.findall(".//t:l", NS)}:
            clash.append(c)
    assert not clash, clash
