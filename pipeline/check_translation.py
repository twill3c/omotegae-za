"""L8 和訳の検査 —— T-01〜T-05(SPEC §5.2)。

**訳の巧拙は測らない。** 測るのは、訳文が原文の構造に従っているかと、
原文にあるものが落ちていないかだけである。どれも意味の判定を経由しない。

  T-01 行対応     原文 <l> 一行 ↔ 訳文一行。欠番・余分・空文字が無い
  T-02 発話の完全性 一つの発話は全訳するか手を付けないか。半端に切らない
  T-03 antilabe   行が話者間で割られている箇所は、訳も別々の行として存在する
  T-04 固有名の一貫 同じギリシア語形は常に同じカタカナ。別の語幹が同じカタカナに
                  なる衝突は原語併記を要求する([[umi-no-ki]] の λ/ρ の教訓)
  T-05 消化率     原文にある固有名・数詞が訳文から落ちていない
                  ([[uta-gaeshi]] G-14/G-15: 訳文側を見る検査では捕まらない)
"""

from __future__ import annotations

import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

NS = {"t": "http://www.tei-c.org/ns/1.0"}
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
TR = ROOT / "data" / "translation"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_reader as BR  # noqa: E402
import speakers as S  # noqa: E402

# ギリシア数詞(基数・序数の語幹)。原文にあれば訳文にも数が要る。
NUMERAL_STEMS = [
    ("μυρι", "万"), ("χιλι", "千"), ("διακοσ", "二百"), ("τριακοσ", "三百"),
    ("ἑκατόν", "百"), ("ἑκατὸν", "百"), ("δέκα", "十"), ("δώδεκα", "十二"),
    ("τρεῖς", "三"), ("τρία", "三"), ("τρι", "三"), ("δύο", "二"), ("δυο", "二"),
    ("ἑπτά", "七"), ("ἑπτὰ", "七"), ("πέντε", "五"), ("τέτταρ", "四"), ("τέσσαρ", "四"),
]

KANA_NUM = "〇一二三四五六七八九十百千万零壱弐参"


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))


def load_names() -> tuple[dict[str, dict], list[str]]:
    """(ギリシア語表層形 → 見出し) と、台帳自体の問題の一覧を返す。"""
    path = TR / "names.json"
    if not path.exists():
        return {}, ["data/translation/names.json が無い"]
    data = json.loads(path.read_text(encoding="utf-8"))
    surface: dict[str, dict] = {}
    problems: list[str] = []
    by_kana: dict[str, set[str]] = defaultdict(set)
    for e in data["entries"]:
        for g in e["grc"]:
            if g in surface and surface[g]["ja"] != e["ja"]:
                problems.append(
                    f"T-04 表層形 {g} が「{surface[g]['ja']}」と「{e['ja']}」の二通りに割り当てられている"
                )
            surface[g] = e
        by_kana[e["ja"]].add(e["stem"])
    for kana, stems in by_kana.items():
        if len(stems) > 1:
            entries = [e for e in data["entries"] if e["ja"] == kana]
            if not all(e.get("homograph") for e in entries):
                problems.append(
                    f"T-04 カタカナ「{kana}」に語幹 {sorted(stems)} が衝突している —— "
                    "原語併記(homograph: true)を明示するか、訳し分ける"
                )
    return surface, problems


def greek_lines(play: str) -> tuple[dict[str, str], list[dict]]:
    """(行番号 → 原文, 発話の一覧) を返す。"""
    path = RAW / f"{play}.perseus-grc2.xml"
    root = ET.parse(path).getroot()
    lines: dict[str, str] = {}
    speeches: list[dict] = []
    prev = None
    for sp in root.findall(".//t:sp", NS):
        lab = S.label_of(sp) or prev
        prev = lab
        ns: list[str] = []
        for e in sp.findall(".//t:l", NS):
            t = BR.grc_text(e)
            if not t:
                continue
            n = e.get("n")
            lines[n] = t
            ns.append(n)
        if ns:
            speeches.append({"who": lab, "lines": ns})
    return lines, speeches


def antilabe_parts(play: str) -> dict[str, str]:
    root = ET.parse(RAW / f"{play}.perseus-grc2.xml").getroot()
    return {
        e.get("n"): e.get("part")
        for e in root.findall(".//t:l", NS)
        if e.get("part") and BR.grc_text(e)
    }


def check(play: str, surface: dict[str, dict]) -> tuple[dict, list[str]]:
    problems: list[str] = []
    tpath = TR / f"{play}.json"
    if not tpath.exists():
        return {"play": play, "translated": 0, "total": 0}, problems
    tr = json.loads(tpath.read_text(encoding="utf-8"))["lines"]
    lines, speeches = greek_lines(play)
    parts = antilabe_parts(play)

    # --- T-01 行対応 -------------------------------------------------------
    extra = sorted(set(tr) - set(lines))
    if extra:
        problems.append(f"T-01 {play}: 原文に無い行番号 {extra[:8]}")
    empty = sorted(n for n, t in tr.items() if not t.strip())
    if empty:
        problems.append(f"T-01 {play}: 訳文が空の行 {empty[:8]}")

    # --- T-02 発話の完全性 -------------------------------------------------
    for sp in speeches:
        done = [n for n in sp["lines"] if n in tr]
        if done and len(done) != len(sp["lines"]):
            miss = [n for n in sp["lines"] if n not in tr]
            problems.append(
                f"T-02 {play}: 発話({sp['who']} {sp['lines'][0]}〜)が半端。未訳 {miss[:6]}"
            )

    # --- T-03 antilabe -----------------------------------------------------
    for n, part in parts.items():
        if n not in tr:
            continue
        # 割られた行は、それぞれ独立した訳文を持たねばならない
        if not tr[n].strip():
            problems.append(f"T-03 {play}: 割られた行 {n}(part={part})の訳が空")
    dup = Counter(tr[n] for n in parts if n in tr)
    for text, k in dup.items():
        if k > 1 and len(text) > 4:
            problems.append(f"T-03 {play}: 割られた行の訳が {k} 箇所で同一「{text[:20]}」")

    # --- T-04 / T-05 固有名と数詞の消化 ------------------------------------
    for n, ja in tr.items():
        grc = lines.get(n, "")
        for w in re.findall(r"[Ͱ-Ͽἀ-῿ʼ']+", grc):
            w = w.strip("'ʼ")
            e = surface.get(w)
            if e and e["ja"] not in ja:
                problems.append(
                    f"T-05 {play} {n}: 原文の {w} に対応する「{e['ja']}」が訳文に無い —— {ja[:28]}"
                )
        # 数詞は**語頭一致**で見る。語中一致にすると στρατιᾶς(軍勢)が
        # 「τρι(三)」に当たるような誤検出が出る(L8 で実際に踏んだ)。
        words = [strip_accents(w).lower() for w in re.findall(r"[Ͱ-Ͽἀ-῿]+", grc)]
        for stem, _kanji in NUMERAL_STEMS:
            st = strip_accents(stem).lower()
            if any(w.startswith(st) for w in words) and not any(c in ja for c in KANA_NUM):
                problems.append(f"T-05 {play} {n}: 原文に数詞({stem})があるが訳文に数が無い —— {ja[:28]}")
                break

    return {"play": play, "translated": len(tr), "total": len(lines)}, problems


def main() -> int:
    surface, problems = load_names()
    plays = sorted(p.name.split(".perseus-")[0] for p in RAW.glob("*.perseus-grc2.xml"))
    rows = []
    for play in plays:
        row, probs = check(play, surface)
        problems += probs
        if row["translated"]:
            rows.append(row)

    done = sum(r["translated"] for r in rows)
    total = sum(len(greek_lines(p)[0]) for p in plays)
    print(f"和訳 {done:,} / 全 {total:,} 行({done / total:.2%})")
    for r in rows:
        print(f"  {r['play']}  {r['translated']:>5} / {r['total']:<5} {r['translated'] / r['total']:>7.1%}")

    if problems:
        print(f"\n問題 {len(problems)} 件:")
        for p in problems[:30]:
            print("  " + p)
        if len(problems) > 30:
            print(f"  … 他 {len(problems) - 30} 件")
        return 1
    print("\nT-01〜T-05 問題 0 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
