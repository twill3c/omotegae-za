"""L8 和訳の検査 —— T-01〜T-07(SPEC §5.2)。

**訳の巧拙は測らない。** 測るのは、訳文が原文の構造に従っているかと、
原文にあるものが落ちていないかだけである。どれも意味の判定を経由しない。

  T-01 行対応     原文 <l> 一行 ↔ 訳文一行。欠番・余分・空文字が無い
  T-02 発話の完全性 一つの発話は全訳するか手を付けないか。半端に切らない
  T-03 antilabe   行が話者間で割られている箇所は、訳も別々の行として存在する
  T-04 固有名の一貫 同じギリシア語形は常に同じカタカナ。別の語幹が同じカタカナに
                  なる衝突は原語併記を要求する([[umi-no-ki]] の λ/ρ の教訓)
  T-05 消化率     原文にある固有名・数詞が訳文から落ちていない
                  ([[uta-gaeshi]] G-14/G-15: 訳文側を見る検査では捕まらない)
  T-07 訳出範囲の穴 訳した範囲の内側に未訳行を残していない。T-02 は発話を
                  **半端に切った**場合しか見ないので、発話ごとまるごと
                  飛ばした穴を素通りする(L19 で実際に素通りした)
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

def load_numerals() -> tuple[list[tuple[str, str]], set[str]]:
    """数詞の見出しと例外を data/translation/numerals.json から読む。

    見出しは語頭一致で当てるが、それだけでは粗い(τρίχα 毛髪が「三」に当たる)。
    例外はアクセントを外した完全形で持ち、**実測で育てる**。
    """
    data = json.loads((TR / "numerals.json").read_text(encoding="utf-8"))
    stems = [(a, b) for a, b in data["stems"]]
    exc = {e["word"] for e in data["exceptions"]}
    return stems, exc


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
    # 同じ語幹が二つの見出しに分かれていないか。
    # カタカナ側の衝突(下)は「一つのカタカナに複数の語幹」しか見ないので、
    # **同じ語幹に二つのカタカナ**という向きは素通りする。L15 で実際に素通りした ——
    # 既存の Δωδων(ドドナ)に気づかず Δωδων(ドドネ)を新設し、同じ地が二通りになった。
    by_stem: dict[str, set[str]] = defaultdict(set)
    for e in data["entries"]:
        by_stem[e["stem"]].add(e["ja"])
    for stem, kanas in by_stem.items():
        if len(kanas) > 1:
            problems.append(
                f"T-04 語幹 {stem} が「{'」「'.join(sorted(kanas))}」の二通りに訳し分けられている —— "
                "同じ見出しにまとめるか、語幹を分ける"
            )

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
    num_stems, num_exc = load_numerals()
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

    # --- T-07 訳出範囲の穴 --------------------------------------------------
    # T-02 は「一つの発話を半端に切らない」ことしか見ないので、**発話ごと
    # まるごと飛ばした穴は素通りする**。L19 で実際に素通りした —— 『七将』
    # 181〜202(エテオクレスの 22 行)を丸ごと飛ばしたまま二ループ進み、
    # 気づいたのは充填率が 98.0% で止まったことだけだった。
    # 訳出済みの最初の行と最後の行のあいだに未訳行があれば、それは穴である。
    order = list(lines)
    idx = [i for i, n in enumerate(order) if n in tr]
    if idx:
        holes = [order[i] for i in range(idx[0], idx[-1] + 1) if order[i] not in tr]
        if holes:
            problems.append(
                f"T-07 {play}: 訳出範囲({order[idx[0]]}〜{order[idx[-1]]})の内側に未訳の穴が "
                f"{len(holes)} 行 {holes[:8]}"
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
        words = [
            w for w in (strip_accents(x).lower() for x in re.findall(r"[Ͱ-Ͽἀ-῿]+", grc))
            if w not in num_exc
        ]
        for stem, _kanji in num_stems:
            st = strip_accents(stem).lower()
            if any(w.startswith(st) for w in words) and not any(c in ja for c in KANA_NUM):
                problems.append(f"T-05 {play} {n}: 原文に数詞({stem})があるが訳文に数が無い —— {ja[:28]}")
                break

    return {"play": play, "translated": len(tr), "total": len(lines)}, problems


def demands(play: str, lo: int, hi: int) -> list[tuple[str, list[str]]]:
    """訳す**前**に、どの行がどのカタカナ・どの数を要求するかを一覧する。

    T-05 は訳し終えてから発火する事後の検査で、実際 L9〜L15 で七度、
    **同じ形**で落ちた —— 原文では属格が次の行の頭にあるのに、日本語では
    「ゼウスの◯◯」と一行に続けたくなるので、固有名が隣の行へ流れる。
    検査は毎回捕まえたが、捕まえるのは書き終えたあとである。

    この関数は同じ台帳を**訳す前**に引く。事後の検査を緩めるのではなく、
    同じ規範を前に置くだけなので、T-05 の厳しさは変わらない。
    """
    surface, _ = load_names()
    num_stems, num_exc = load_numerals()
    lines, _sp = greek_lines(play)
    out: list[tuple[str, list[str]]] = []
    for n, grc in lines.items():
        try:
            k = int(re.sub(r"\D", "", n) or 0)
        except ValueError:  # pragma: no cover
            continue
        if not lo <= k <= hi:
            continue
        want: list[str] = []
        for w in re.findall(r"[Ͱ-Ͽἀ-῿ʼ']+", grc):
            e = surface.get(w.strip("'ʼ"))
            if e and e["ja"] not in want:
                want.append(e["ja"])
        words = [
            w for w in (strip_accents(x).lower() for x in re.findall(r"[Ͱ-Ͽἀ-῿]+", grc))
            if w not in num_exc
        ]
        for stem, kanji in num_stems:
            st = strip_accents(stem).lower()
            if any(w.startswith(st) for w in words) and kanji not in want:
                want.append(kanji)
        if want:
            out.append((n, want))
    return out


def main() -> int:
    if len(sys.argv) >= 5 and sys.argv[1] == "demands":
        play, lo, hi = sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
        rows = demands(play, lo, hi)
        for n, want in rows:
            print(f"  {n:>5}  {' / '.join(want)}")
        print(f"{lo}〜{hi} 行のうち {len(rows)} 行が固有名・数詞を要求する")
        return 0

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
    print("\nT-01〜T-07 問題 0 件")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
