"""L6 リーダー用データ —— 原文を行番号のまま読み、英訳を並べる。

## 対応づけ

英訳 TEI の `<l n="…">` は、その塊が始まる**原文の行番号**を指す(散文訳は数行ぶんを
一塊にする)。したがって錨(anchor)は原文の行番号そのものであり、
**対応づけに意味の判定は要らない**。

### 錨が原文に無いことがある(L6 実測 2026-09-02)

19,000 件弱の錨のうち 112 件(0.6%)が原文の行番号集合に無い。内訳に構造がある:

- **ソポクレス 1.7〜2.9%** —— 原文は Storr の校訂、英訳は Jebb の校訂で、**版が違う**
- アイスキュロス・エウリピデス・アリストパネス 0.6% 以下
  (アイスキュロスは原文も英訳も Smyth で、同じ版の訳)

これは SPEC §2.1 の交絡(校訂者が篇ごとに違う)が対応づけにも及ぶことの実例である。
**錨が合わない件数は篇ごとに数えて画面に出す。** 黙って近い行に寄せない。

錨に加えて `'5563'`(ヘレネ)や `'4097'`(嘆願する女たち)のような明らかな誤植もある。
これらは数値部で近傍に寄せず、**対応づけ不能として数える**。
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"t": "http://www.tei-c.org/ns/1.0"}
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
RAW_ENG = ROOT / "data" / "raw_eng"
SITE = ROOT / "src" / "data" / "reader"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import speakers as S  # noqa: E402


def text_of(el, skip: frozenset[str] = frozenset(), grab: frozenset[str] = frozenset()) -> tuple[str, list[str]]:
    """本文と、抜き出した要素の中身を返す。

    `itertext()` を素直に使うと、**校訂者の脚注や訳者のト書きが本文に溶け込む**。
    実測 2026-09-02: 英訳の `<l>` 内に脚注 687 件・ト書き 454 件があり、
    そのまま連結すると「訳文」と「注釈」の区別が付かなくなる。

    原文側で落とすのは `<note>`(49 件)だけにする。`<add>` `<del>` `<sic>` `<gap>` は
    **校訂者が提示した本文そのもの**なので残す(『追跡者たち』のパピルスは
    `]γ[]λ[` のような欠損表記が本文である)。
    """
    parts: list[str] = []
    grabbed: list[str] = []

    def walk(node, top=False):
        tag = node.tag.split("}")[-1]
        if not top and tag in skip:
            # 飛ばすのは要素の中身だけ。**その後ろに続く本文(tail)は本文である。**
            # ここを落とすと、注記のあとに続く語が黙って消える(L6 で踏んだ)。
            if node.tail:
                parts.append(node.tail)
            return
        if not top and tag in grab:
            grabbed.append(" ".join("".join(node.itertext()).split()))
            if node.tail:
                parts.append(node.tail)
            return
        if node.text:
            parts.append(node.text)
        for ch in node:
            walk(ch)
        if not top and node.tail:
            parts.append(node.tail)

    walk(el, top=True)
    return " ".join("".join(parts).split()), [g for g in grabbed if g]


GRC_SKIP = frozenset({"note"})
ENG_SKIP = frozenset({"note"})
ENG_GRAB = frozenset({"stage"})


def grc_text(el) -> str:
    return text_of(el, skip=GRC_SKIP)[0]


def greek_speeches(path: Path, ledger: dict) -> list[dict]:
    play = path.name.split(".perseus-")[0]
    root = ET.parse(path).getroot()
    out: list[dict] = []
    prev = None
    for sp in root.findall(".//t:sp", NS):
        lab = S.label_of(sp)
        inherited = lab is None
        if inherited:
            if prev is None:
                raise AssertionError(f"{play}: 継承元の無い話者欠落")
            lab = prev
        prev = lab
        rec = ledger.get((play, lab))
        cls = rec["class"] if rec else "actor"
        if cls == "merge":
            lab = rec["merge_into"]
            cls = "actor"
        lines = []
        for e in sp.findall(".//t:l", NS):
            t = grc_text(e)
            if t:  # 本文が空の行は落とす(実測 121 件)
                lines.append([e.get("n"), t])
        if not lines:
            continue
        out.append({"who": lab, "cls": cls, "inherited": inherited, "lines": lines})
    return out


def english_blocks(path: Path) -> dict:
    root = ET.parse(path).getroot()
    m = root.find(".//t:sourceDesc//t:monogr", NS)
    editors = [text_of(e)[0] for e in m.findall("t:editor", NS)] if m is not None else []
    title = text_of(m.find("t:title", NS))[0] if m is not None and m.find("t:title", NS) is not None else ""
    date = text_of(m.find(".//t:date", NS))[0] if m is not None and m.find(".//t:date", NS) is not None else ""
    blocks = []
    notes = stages = 0
    for e in root.findall(".//t:l", NS):
        n = e.get("n")
        notes += len(e.findall(".//t:note", NS))
        t, st = text_of(e, skip=ENG_SKIP, grab=ENG_GRAB)
        stages += len(st)
        if n and (t or st):
            blocks.append([n, t, st])
    return {
        "translator": " / ".join(x for x in editors if x) or "(記載なし)",
        "source": title,
        "date": date,
        "blocks": blocks,
        "notes_dropped": notes,
        "stages": stages,
    }


def pick_english(play: str) -> tuple[str | None, list[str]]:
    """既定の英訳と、他に存在する版の一覧。版番号の小さい方を既定にする。"""
    found = sorted(
        p.name.rsplit(".perseus-", 1)[1][:4]
        for p in RAW_ENG.glob(f"{play}.perseus-*.xml")
    )
    return (found[0] if found else None, found[1:])


def main() -> int:
    ledger = {(r["play"], r["label"]): r for r in json.loads((ROOT / "data" / "derived" / "speakers.json").read_text(encoding="utf-8"))}
    SITE.mkdir(parents=True, exist_ok=True)
    report = {}

    for path in sorted(RAW.glob("*.perseus-grc2.xml")):
        play = path.name.split(".perseus-")[0]
        speeches = greek_speeches(path, ledger)
        gline_ns = {n for s in speeches for n, _t in s["lines"]}

        ver, others = pick_english(play)
        en = None
        matched = unmatched = 0
        if ver:
            en = english_blocks(RAW_ENG / f"{play}.perseus-{ver}.xml")
            anchored: dict[str, str] = {}
            stages: dict[str, list[str]] = {}
            for n, t, st in en["blocks"]:
                if n in gline_ns:
                    # 同じ錨に複数塊が付くことがある(散文訳の段落分け)
                    if t:
                        anchored[n] = (anchored.get(n, "") + " " + t).strip()
                    if st:
                        stages.setdefault(n, []).extend(st)
                    matched += 1
                else:
                    unmatched += 1
            en = {
                "version": ver,
                "others": others,
                "translator": en["translator"],
                "source": en["source"],
                "date": en["date"],
                "anchored": anchored,
                "stages": stages,
                "notes_dropped": en["notes_dropped"],
            }

        tr_path = ROOT / "data" / "translation" / f"{play}.json"
        ja = {}
        ja_meta = None
        if tr_path.exists():
            t = json.loads(tr_path.read_text(encoding="utf-8"))
            ja = t["lines"]
            ja_meta = {k: t.get(k, "") for k in ("translator", "license", "base", "note")}
            # 和訳の行番号は原文に実在しなければならない(T-01)
            unknown = sorted(set(ja) - gline_ns)
            if unknown:
                raise AssertionError(f"{play}: 原文に無い行に訳がある {unknown[:6]}")

        payload = {
            "id": play,
            "speeches": speeches,
            "en": en,
            "ja": ja,
            "ja_meta": ja_meta,
            "ja_count": len(ja),
            "align": {
                "matched": matched,
                "unmatched": unmatched,
                "blocks": matched + unmatched,
            },
        }
        (SITE / f"{play}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8"
        )

        # G-02 と同型の検算: 落とした空行を除き、原文の行が一つも欠けていない
        root = ET.parse(path).getroot()
        nonempty = sum(1 for e in root.findall(".//t:l", NS) if grc_text(e))
        kept = sum(len(s["lines"]) for s in speeches)
        if kept != nonempty:
            raise AssertionError(f"{play}: 本文のある行 {nonempty} に対しリーダーに {kept}")

        report[play] = {
            "lines": kept,
            "ja": len(ja),
            "speeches": len(speeches),
            "en": ver,
            **payload["align"],
        }

    (ROOT / "data" / "derived" / "reader_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    total = sum(p.stat().st_size for p in SITE.glob("*.json"))
    big = sorted(SITE.glob("*.json"), key=lambda p: -p.stat().st_size)[:3]
    with_en = sum(1 for v in report.values() if v["en"])
    um = sum(v["unmatched"] for v in report.values())
    bl = sum(v["blocks"] for v in report.values())
    print(f"45 篇 / 英訳あり {with_en} 篇")
    print(f"錨 {bl:,} 件中 対応不能 {um} 件({um / max(1, bl):.2%})")
    print(f"合計 {total / 1024 / 1024:.2f} MB  最大: " + ", ".join(f"{p.name} {p.stat().st_size / 1024:.0f}KB" for p in big))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
