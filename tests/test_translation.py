"""L8 和訳の検査そのものを検査する。

**落ちない検査は検査ではない。** T-01〜T-05 のそれぞれについて、
わざと壊した訳文を作り、その検査が実際に発火することを確かめる(陽性対照)。
HC-070 に従い、対照の本体に「壊した箇所が実際に効く入力である」ことを書く。
"""

from __future__ import annotations

import json
import re
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
def test_T07_発話をまるごと飛ばすと落ちる(tr_file, surface):
    """T-02 の**盲点**の対照。

    T-02 は「一つの発話を半端に切らない」ことしか見ないので、発話を
    **まるごと**飛ばした穴は「手を付けていない」扱いで素通りする。
    L19 で実際に素通りした —— 『七将』181〜202(エテオクレスの 22 行)を
    丸ごと飛ばしたまま二ループ進み、気づいたのは充填率が 98.0% で
    止まったことだけだった。

    そこで**発話を一つ丸ごと抜き**、T-02 は黙り、T-07 が発火することを確かめる。
    両方を主張しないと「T-07 が T-02 の言い換えでない」ことが示せない。
    """
    _lines, speeches = CT.greek_lines(PLAY)
    # 前後を訳したままにできる、真ん中あたりの発話を選ぶ
    target = next(s for s in speeches[2:] if len(s["lines"]) >= 3)
    d = _load(tr_file)
    for n in target["lines"]:
        del d["lines"][n]
    _save(tr_file, d)
    _row, problems = CT.check(PLAY, surface)
    assert not [p for p in problems if p.startswith("T-02")], problems
    assert any(p.startswith("T-07") and target["lines"][0] in p for p in problems), problems


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
def test_数詞の例外は実際に見出しに当たる語である():
    """**死んだ例外を作らない。**

    例外表の語は (1) 45 篇の原文に実在し、(2) 見出しのどれかに語頭一致して
    はじめて意味を持つ。当たらない語を例外に入れても検出は変わらないので、
    それは確かめずに書いた例外である(HC-120 の「表が実データから外れる」型)。
    """
    import xml.etree.ElementTree as ET

    NS = {"t": "http://www.tei-c.org/ns/1.0"}
    stems, exc = CT.load_numerals()
    assert exc, "例外表が空 —— 検査が空回りしている"

    seen: set[str] = set()
    for p in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        for e in ET.parse(p).getroot().findall(".//t:l", NS):
            for w in re.findall(r"[Ͱ-Ͽἀ-῿]+", "".join(e.itertext())):
                seen.add(CT.strip_accents(w).lower())

    dead = sorted(w for w in exc if w not in seen)
    assert not dead, f"原文に現れない例外: {dead}"

    useless = sorted(
        w
        for w in exc
        if not any(w.startswith(CT.strip_accents(s).lower()) for s, _k in stems)
    )
    assert not useless, f"どの見出しにも当たらない例外: {useless}"


@pytest.mark.validation
def test_数詞の例外に理由が書いてある():
    data = json.loads((ROOT / "data" / "translation" / "numerals.json").read_text(encoding="utf-8"))
    for e in data["exceptions"]:
        assert e["reason"].strip(), e


@pytest.mark.validation
def test_台帳から外した表層形は台帳に載っていない(surface):
    """同一表層形が別物を指す語は、台帳に入れてはならない(excluded に理由付きで残す)。

    L10 実測: `Μάρδων` は 51 行が人名マルドン、993 行が民族名の属格複数。
    台帳に入れると T-05 が片方に誤訳を強制する。
    """
    data = json.loads((ROOT / "data" / "translation" / "names.json").read_text(encoding="utf-8"))
    excluded = data.get("excluded", [])
    assert excluded, "excluded が空 —— この検査が空回りしている"
    for e in excluded:
        assert e["reason"].strip(), e
        assert e["grc"] not in surface, f"{e['grc']} は excluded なのに台帳にある"


@pytest.mark.validation
def test_T04_同じ語幹が二つのカタカナに分かれると落ちる(tmp_path, monkeypatch):
    """衝突検査の**向き**の対照。

    カタカナ側の検査は「一つのカタカナに複数の語幹」しか見ない。逆向き ——
    同じ語幹を二つのカタカナに割ってしまう誤り —— は L15 で実際に素通りし、
    既存の Δωδων(ドドナ)に気づかないまま Δωδων(ドドネ)を新設して、
    同じ神託所が二通りの表記で出荷される寸前まで行った。
    """
    work = tmp_path / "translation"
    work.mkdir()
    (work / "names.json").write_text(
        json.dumps(
            {
                "_": [],
                "entries": [
                    {"stem": "Δωδων", "ja": "ドドナ", "grc": ["Δωδωναῖα"]},
                    {"stem": "Δωδων", "ja": "ドドネ", "grc": ["Δωδώνης"]},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(CT, "TR", work)
    _s, problems = CT.load_names()
    assert any("Δωδων" in p and "二通り" in p for p in problems), problems


@pytest.mark.validation
def test_訳す前の一覧は訳したあとの検査と一致する(tr_file, surface):
    """`demands` は T-05 を**前に置いた**だけで、緩めた版であってはならない。

    L15 で入れた事前一覧は、事後の T-05 と同じ台帳・同じ数詞表を引く。
    両者がずれていれば、事前に緑でも事後に落ちる(あるいはその逆で、
    事前一覧が実際には守らせていない)ことになる。

    そこで**一覧が要求した語を実際に訳文から抜き**、T-05 がその行で
    発火することを確かめる。要求と検出が同じ行・同じ語で対応してはじめて、
    事前一覧は事後の検査の代わりに読める。
    """
    rows = CT.demands(PLAY, 1, 120)
    assert rows, "ペルシア人 1〜120 行に固有名が一つも無いはずがない"
    n, want = rows[0]
    d = _load(tr_file)
    assert want[0] in d["lines"][n], (n, want, d["lines"][n])
    d["lines"][n] = "……"
    _save(tr_file, d)
    _row, problems = CT.check(PLAY, surface)
    assert any(p.startswith("T-05") and f" {n}:" in p for p in problems), (n, want, problems)


@pytest.mark.validation
def test_訳す前の一覧は範囲外の行を出さない():
    rows = CT.demands(PLAY, 40, 60)
    assert rows
    assert all(40 <= int(re.sub(r"\D", "", n) or 0) <= 60 for n, _w in rows), rows


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


@pytest.mark.validation
def test_除外行の表は生きている():
    """`skip_lines` は「空ではないが本文でもない <l>」の列挙。

    死んだ列挙を作らない —— 表に書いた行が (1) 原本に実在し、(2) 本文が空でなく
    (空なら既存の処理で落ちるので列挙は無意味)、(3) 実際に訳出対象から
    外れていること、を確かめる。理由が書かれていることも要求する。

    L20 実測: 45 篇の `n="0"` は 30 篇すべて本文が空で自然に落ちるが、
    『アガメムノン』の一件だけ語(話者名 Φύλαξ)が入っていて訳出対象に混じっていた。
    """
    import xml.etree.ElementTree as ET

    NS = {"t": "http://www.tei-c.org/ns/1.0"}
    skip = CT.BR.skipped_lines()
    assert skip, "skip_lines が空 —— この検査が空回りしている"
    for (play, n), reason in skip.items():
        assert reason.strip(), (play, n)
        root = ET.parse(ROOT / "data" / "raw" / f"{play}.perseus-grc2.xml").getroot()
        hit = [e for e in root.findall(".//t:l", NS) if e.get("n") == n]
        assert hit, f"原本に無い行を除外している: {play} {n}"
        assert CT.BR.grc_text(hit[0]).strip(), (
            f"{play} {n} は本文が空 —— 既存の空行処理で落ちるので列挙は不要"
        )
        lines, _sp = CT.greek_lines(play)
        assert n not in lines, f"{play} {n} が除外されていない"


@pytest.mark.validation
def test_数詞の例外は語族ごとに埋まっている():
    """**同じ語族の取りこぼしを残さない。**

    誤発火した語を一件ずつ足していると、同じ語族の別の語形が残る ——
    L19 で τρίχ-(毛)、L21 で τρίβ-(擦る)が二度それで露呈した。

    そこで「例外のある語族に属するのに、例外でも confirmed でもない語」が
    45 篇に無いことを要求する。`confirmed` は「語族が同じだが**数詞である**」ことを
    明示する側の表で、どちらかに必ず入れれば判定漏れが残らない。

    **語族の切れ目は見出しの次の一文字**(τρι+β = τριβ)。L21 は 5 文字前方一致で
    切ったが、τρίβειν が τριβω と結ばれず素通りして L23 で誤発火した。
    """
    import xml.etree.ElementTree as ET

    NS = {"t": "http://www.tei-c.org/ns/1.0"}
    stems, exc = CT.load_numerals()
    data = json.loads((ROOT / "data" / "translation" / "numerals.json").read_text(encoding="utf-8"))
    confirmed = {e["word"] for e in data.get("confirmed", [])}
    assert confirmed, "confirmed が空 —— この検査が空回りしている"
    for e in data["confirmed"]:
        assert e["reason"].strip(), e

    heads = [CT.strip_accents(s).lower() for s, _k in stems]
    seen: set[str] = set()
    for p in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        for el in ET.parse(p).getroot().findall(".//t:l", NS):
            for w in re.findall(r"[Ͱ-Ͽἀ-῿]+", "".join(el.itertext())):
                seen.add(CT.strip_accents(w).lower())

    def family(w: str) -> str | None:
        """語族の切れ目は**見出しの次の一文字**。τρι+β = τριβ、ἑπτά+τ = επτατ。"""
        hs = [h for h in heads if w.startswith(h)]
        if not hs:
            return None
        h = max(hs, key=len)
        return w[: len(h) + 1] if len(w) > len(h) else None

    fams = {family(x) for x in exc} - {None}
    unresolved = sorted(
        w for w in seen if family(w) in fams and w not in exc and w not in confirmed
    )
    assert not unresolved, f"語族が例外に触れているのに判定していない語: {unresolved}"


@pytest.mark.validation
def test_ギリシア文字を含まない行はすべて除外表に載っている():
    """**本文でない <l> の取りこぼしを残さない。**

    ギリシア文字を一つも含まない `<l>` は、本文ではなく校訂者の記号である
    (欠落を示すダッシュ、失われた行の韻律記号)。L32 実測で 45 篇に 2 件あり、
    どちらも `skip_lines` に列挙した。

    ここで「ギリシア文字が無ければ落とす」という機械の規則は**書かない** ——
    列挙を保ったまま、**新しい件が出たら検査が落ちて人が判定する**ようにする。
    数詞の語族と同じ構えである。
    """
    import xml.etree.ElementTree as ET

    NS = {"t": "http://www.tei-c.org/ns/1.0"}
    skip = CT.BR.skipped_lines()
    unlisted = []
    for p in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        play = p.name.split(".perseus")[0]
        for e in ET.parse(p).getroot().findall(".//t:l", NS):
            t = CT.BR.grc_text(e)
            if t and not re.search(r"[Ͱ-Ͽἀ-῿]", t) and (play, e.get("n")) not in skip:
                unlisted.append((play, e.get("n"), t))
    assert not unlisted, f"ギリシア文字を含まないのに除外表に無い <l>: {unlisted}"
