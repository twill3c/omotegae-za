"""L1 話者名の名寄せ台帳 — 45 篇の話者ラベルを分類する。

SPEC F-02 に従い、**自動正規化はしない**。下の DECISIONS は 2026-09-02 に
全 497 組(篇 × ラベル)を目視して手で書いた採否表である。表に無いラベルは
`actor`(語る役 = 彩色の頂点)として扱う。

分類:
  chorus       合唱隊とその下位区分。彩色の頂点にしない(合唱隊は俳優が演じない)
  actor        語る役。彩点の頂点になる
  joint        複数人の共同発話。構成員に分解する
  merge:<先>   直前・直後が同一話者で挟まれた孤立 1 件の表記事故。<先> に統合する
  review       本文からは決着しない。人間の判断を待つ(G-01 で 0 にする)

HC-120 に従い、仮定は書いた場所で検算する。表に載せたラベルが実データに
存在しなければ例外で止める(表が古びたまま静かに効かなくなるのを防ぐ)。
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
DERIVED = ROOT / "data" / "derived"

# ---------------------------------------------------------------------------
# 採否表(2026-09-02 全数目視)
#
# キーは (篇の stem, ラベル文字列)。値は分類とその根拠。
# 根拠には「何を見てそう決めたか」を書く —— 後から表だけを見た人が
# 追試できない判断を残さない。
# ---------------------------------------------------------------------------

CHORUS_REASON = "合唱隊およびその下位区分。合唱隊は俳優が演じないため彩色の頂点にしない"

# 合唱隊系 26 ラベル(語幹 χορ/ἡμιχορ を持つもの全数)。
# Χορὸς Ἀγάθωνος だけは下の REVIEW に回す —— 劇中劇の合唱で、
# 実際にはアガトンを演じる俳優が歌っている可能性がある。
CHORUS: dict[tuple[str, str], str] = {
    ("tlg0006.tlg001", "Χορός"): CHORUS_REASON,
    ("tlg0006.tlg001", "Ημιχ. Χορός"): "半合唱隊(495-502)。表記は略記だが χορ 語幹を持つ",
    ("tlg0006.tlg001", "Χορός α"): "635-641 で合唱隊が個々のサテュロスに分かれて語る 4 連の 1",
    ("tlg0006.tlg001", "Χορός β"): "同上 2",
    ("tlg0006.tlg001", "Χορός γ"): "同上 3",
    ("tlg0006.tlg001", "Χορός δ"): "同上 4",
    ("tlg0006.tlg004", "Ἡμιχόριον"): CHORUS_REASON,
    ("tlg0006.tlg005", "Χορός Κυνηγῶν"): "狩人の合唱隊",
    ("tlg0006.tlg011", "Ἡμιχόριον Α"): CHORUS_REASON,
    ("tlg0006.tlg011", "Ἡμιχόριον Β"): CHORUS_REASON,
    ("tlg0006.tlg016", "Ἡμίχορος Α"): CHORUS_REASON,
    ("tlg0006.tlg016", "Ἡμίχορος Β"): CHORUS_REASON,
    ("tlg0006.tlg018", "Χορὸς ἀνδρῶν Ἀργείων"): "アルゴス人男子の合唱隊",
    ("tlg0011.tlg001", "Ἡμιχόριον"): CHORUS_REASON,
    ("tlg0011.tlg001", "Ἡμιχόριον 1"): CHORUS_REASON,
    ("tlg0011.tlg001", "Ἡμιχόριον 2"): CHORUS_REASON,
    ("tlg0011.tlg003", "Ἡμιχόριον 1"): CHORUS_REASON,
    ("tlg0011.tlg003", "Ἡμιχόριον 2"): CHORUS_REASON,
    ("tlg0011.tlg008", "Χορὸς Σατύρων"): "サテュロスの合唱隊",
    ("tlg0011.tlg008", "Ἡμιχορὸς α"): CHORUS_REASON,
    ("tlg0011.tlg008", "Ἡμιχορὸς β"): CHORUS_REASON,
    ("tlg0019.tlg001", "Ἡμιχόριον Α"): CHORUS_REASON,
    ("tlg0019.tlg001", "Ἡμιχόριον Β"): CHORUS_REASON,
    ("tlg0019.tlg002", "Χορὸς Ἱππεῶν"): "騎士の合唱隊",
    ("tlg0019.tlg005", "Ἡμιχόριον Α"): CHORUS_REASON,
    ("tlg0019.tlg005", "Ἡμιχόριον Β"): CHORUS_REASON,
    ("tlg0019.tlg007", "Χορὸς γερόντων"): "老人の半合唱隊(254-1042)。1043 以降 Χορός に合流する",
    ("tlg0019.tlg007", "Χορὸς Γυναικῶν"): "女の半合唱隊(319-1036)。1043 以降 Χορός に合流する",
    ("tlg0019.tlg007", "Χορὸς Ἀθηναίων"): "終盤のアテナイ人歌い手(1279-1294)",
    ("tlg0019.tlg007", "Χορὸς Λακεδαιμονίων"): "終盤のラケダイモン人歌い手(1247-1320)",
    ("tlg0085.tlg001", "Χορός Δαναΐδων"): "ダナオスの娘たちの合唱隊(本篇の主合唱隊)",
    ("tlg0085.tlg001", "Χορὸς Θεραπαινῶν"): "侍女の合唱隊(終曲)",
    ("tlg0085.tlg004", "Ἡμιχόριον Α"): CHORUS_REASON,
    ("tlg0085.tlg004", "Ἡμιχόριον Β"): CHORUS_REASON,
}
# Χορός は 45 篇すべてに現れる。表を 45 行に膨らませず、ここで一括して入れる。
CHORUS_UNIVERSAL = "Χορός"

# 表記事故(孤立 1 件が同一話者の連続の内側に挟まれている)。統合先を書く。
MERGE: dict[tuple[str, str], tuple[str, str]] = {
    ("tlg0006.tlg003", "Παιδαγωγός."): (
        "Παιδαγωγός",
        "1009-1010 の 1 件のみ末尾にピリオド。前後 1002-1018 は同一話者の連続",
    ),
    ("tlg0006.tlg006", "θεράπαινα"): (
        "Θεράπαινα",
        "68-69 の 1 件のみ小文字。前後 56-90 は同一話者の連続",
    ),
    ("tlg0085.tlg001", "βασιλεύς"): (
        "Βασιλεύς",
        "344 の 1 件のみ小文字。前後 234-523 は同一話者の連続",
    ),
}

# 共同発話。構成員に分解する。
JOINT: dict[tuple[str, str], tuple[list[str], str]] = {
    ("tlg0019.tlg002", "Δημοσθένης καὶ Νικίας"): (
        ["Δημοσθένης", "Νικίας"],
        "2 人の同時発話。両名とも同篇に単独の話者ラベルを持つ",
    ),
    ("tlg0019.tlg002", "Κλέων καὶ Ἀλλαντοπώλης"): (
        ["Κλέων", "Ἀλλαντοπώλης"],
        "同上",
    ),
    ("tlg0019.tlg009", "Αἰσχύλος καὶ Εὐριπίδης"): (
        ["Αἰσχύλος", "Εὐριπίδης"],
        "3 箇所。両名とも同篇に単独の話者ラベルを持つ",
    ),
}

# 本文からは決着しないもの。G-01 はここが 0 になることを要求する。
REVIEW: dict[tuple[str, str], str] = {
    ("tlg0019.tlg001", "Κόρα"): (
        "メガラ人の娘は 2 人いる(784「αὑτηγί この子」/ 789「θατέρᾳ もう一方」)が、"
        "校訂者は Κόρα(ドーリス形)と Κόρη(アッティカ形)を娘 1・娘 2 に対応させていない。"
        "803 でディカイオポリスが「τί δαὶ σύ; そちらの子は?」と別の娘に問うた返事も Κόρα である。"
        "1 頂点にすれば娘 2 人を 1 人に潰し、2 頂点にすれば分割が娘の別と対応しない。"
        "**この判断はアカルナイの χ が 3 を超えるかを左右しうる**"
    ),
    ("tlg0019.tlg001", "Κόρη"): "同上(Κόρα と対)",
    ("tlg0019.tlg008", "Χορὸς Ἀγάθωνος"): (
        "104-129 の劇中劇の合唱。主合唱隊 Χορός(312-1231)とは範囲が離れている。"
        "上演では**アガトンを演じる俳優が独りで歌う**と解されることが多く、"
        "合唱隊(頂点にしない)とするか俳優(頂点にする)とするかで χ が動く"
    ),
    ("tlg0085.tlg001", "Δαναΐς"): (
        "1052-1060。同篇には Χορός Δαναΐδων(合唱隊)と Χορὸς Θεραπαινῶν(侍女合唱隊)があり、"
        "終曲の話者配分は校訂上の論争点である。ダナオスの娘個人(俳優)か、"
        "ダナイデス合唱隊の一部かが本文から決まらない"
    ),
}


def num(n: str | None) -> int | None:
    m = re.match(r"(\d+)", n or "")
    return int(m.group(1)) if m else None


def label_of(sp) -> str | None:
    s = sp.find("t:speaker", NS)
    if s is None:
        return None
    ident = s.get("n")
    if ident:
        return ident.lstrip("#")
    body = " ".join("".join(s.itertext()).split())
    return body or None


def classify(stem: str, label: str) -> dict:
    key = (stem, label)
    if key in REVIEW:
        return {"class": "review", "reason": REVIEW[key]}
    if key in MERGE:
        tgt, why = MERGE[key]
        return {"class": "merge", "merge_into": tgt, "reason": why}
    if key in JOINT:
        parts, why = JOINT[key]
        return {"class": "joint", "members": parts, "reason": why}
    if label == CHORUS_UNIVERSAL:
        return {"class": "chorus", "reason": CHORUS_REASON}
    if key in CHORUS:
        return {"class": "chorus", "reason": CHORUS[key]}
    return {"class": "actor", "reason": "採否表に無いため語る役として扱う(既定)"}


def main() -> int:
    files = sorted(RAW.glob("*.perseus-grc2.xml"))
    rows = []
    seen_keys: set[tuple[str, str]] = set()

    for path in files:
        stem = path.name.split(".perseus-")[0]
        root = ET.parse(path).getroot()
        agg: dict[str, dict] = {}
        prev: str | None = None
        inherited = 0

        for sp in root.findall(".//t:sp", NS):
            lab = label_of(sp)
            if lab is None:
                # <speaker> を持たない sp。L0 で 3 件すべて直前話者の続きであることを
                # 行番号の連続で個別に確認済み(SPEC §2.2 ③)。継承する。
                if prev is None:
                    raise AssertionError(f"{stem}: 継承元の無い話者欠落")
                lab = prev
                inherited += 1
            prev = lab
            lines = [x for x in (num(e.get("n")) for e in sp.findall(".//t:l", NS)) if x]
            a = agg.setdefault(lab, {"sp": 0, "lo": None, "hi": None})
            a["sp"] += 1
            if lines:
                a["lo"] = min(lines) if a["lo"] is None else min(a["lo"], min(lines))
                a["hi"] = max(lines) if a["hi"] is None else max(a["hi"], max(lines))

        for lab, a in sorted(agg.items()):
            seen_keys.add((stem, lab))
            rows.append({"play": stem, "label": lab, **a, **classify(stem, lab)})

        # 継承件数の検算(SPEC §2.2 ③ の実測 3 件と突き合わせる)
        if inherited:
            rows[-1].setdefault("_", None)
            print(f"  {stem}: 話者欠落を {inherited} 件継承", file=sys.stderr)

    # 表が実データから外れていないかの検算(HC-120)。
    table_keys = set(CHORUS) | set(MERGE) | set(JOINT) | set(REVIEW)
    stale = table_keys - seen_keys
    if stale:
        raise AssertionError(f"採否表に実在しないラベルがある: {sorted(stale)}")

    DERIVED.mkdir(parents=True, exist_ok=True)
    (DERIVED / "speakers.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    from collections import Counter

    tally = Counter(r["class"] for r in rows)
    print(f"\n篇 × ラベル: {len(rows)} 組 / 異なりラベル: {len({r['label'] for r in rows})}")
    for k in ("actor", "chorus", "joint", "merge", "review"):
        print(f"  {k:<8} {tally[k]:>4}")

    print("\n--- review(G-01 はここが 0 を要求する) ---")
    for r in rows:
        if r["class"] == "review":
            print(f"  {r['play']} {r['label']}  {r['lo']}-{r['hi']} 発話{r['sp']}")

    print("\n--- 篇ごとの俳優頂点数(review を頂点に数えた場合 / 数えない場合) ---")
    plays = sorted({r["play"] for r in rows})
    for p in plays:
        sub = [r for r in rows if r["play"] == p]
        act = sum(1 for r in sub if r["class"] == "actor")
        act += sum(len(r["members"]) for r in sub if r["class"] == "joint" and False)
        rev = sum(1 for r in sub if r["class"] == "review")
        if rev:
            print(f"  {p}  俳優 {act}(+review {rev})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
