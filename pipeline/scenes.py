"""L2 場面分割 — 合唱隊の発話を境界として、厳・緩の二通りで場面を切る。

## 境界の定め方

本文に退場は書かれていない(ト書きは近代の編者の補い)。合唱隊の歌が登退場を
許すという上演上の性質を使って境界を置く。閾値は結果から逆算しない(G-04)。

- **緩** —— 合唱隊の発話 1 件で切る。場面は細かくなり、衝突は減り、χ は小さく出る
- **厳** —— **合唱隊だけで構成される div** で切る。場面は大きくなり、衝突は増え、χ は大きく出る

**厳が反証側である。**「χ ≤ 3」を主張したいなら、厳で通ることを示さねばならない。

## なぜ行数の閾値を使わないか(L2 実測 2026-09-02)

合唱隊 2,763 発話の長さの分布に谷が無い(1 行 747 / 2 行 512 / 3 行 240 …と
単調に減衰する)。「合唱隊長の短い受け answers」と「本格的な合唱歌」を分ける
自然な閾値は**データが与えてくれない**。閾値を自分で決めれば、その値は結果を
見て動かせてしまう(G-04 違反)。

## なぜ div/@subtype の語彙を裁定しないか(L2 実測 2026-09-02)

subtype は 56 種あり、大文字小文字の揺れ(episode/Episode、choral/Choral、
epirrheme/Epirrheme/epirrhema)を含めて**校訂者ごとにばらけている**(SPEC §2.1)。
`@rend` に至っては アイスキュロス 0.1% / ソポクレス 0.0% / エウリピデス 25.5% /
アリストパネス 11.8% で、韻文種別の手がかりには使えない。

そこで**語彙を判定に使わない**。div の境界だけを編者から借り、
「その div の中で語るのが合唱隊だけか」は L1 の話者分類から決める。
どの subtype が実際に境界になったかは**結果として**出力し、後から見て
妥当かを確かめられるようにする(循環しない検算)。
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

NS = {"t": "http://www.tei-c.org/ns/1.0"}
ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DERIVED = ROOT / "data" / "derived"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import speakers as S  # noqa: E402

# ---------------------------------------------------------------------------
# 決着しない 4 組の読み(SPEC §3.4)。両方の読みで χ を出すため、
# review ラベルに代替の分類を与える。
# ---------------------------------------------------------------------------
READINGS: dict[str, dict[tuple[str, str], str]] = {
    # 読み A: 校訂者のラベルをそのまま別の役として扱う(頂点を多く取る)
    "A": {
        ("tlg0019.tlg001", "Κόρα"): "actor",
        ("tlg0019.tlg001", "Κόρη"): "actor",
        ("tlg0019.tlg008", "Χορὸς Ἀγάθωνος"): "actor",
        ("tlg0085.tlg001", "Δαναΐς"): "actor",
    },
    # 読み B: 争点のある側に寄せる(娘 2 人を 1 頂点に潰し、劇中劇の合唱と
    #         ダナイスを合唱隊に入れる)
    "B": {
        ("tlg0019.tlg001", "Κόρα"): "actor",
        ("tlg0019.tlg001", "Κόρη"): "merge:Κόρα",
        ("tlg0019.tlg008", "Χορὸς Ἀγάθωνος"): "chorus",
        ("tlg0085.tlg001", "Δαναΐς"): "chorus",
    },
}


def load_ledger() -> dict[tuple[str, str], dict]:
    path = DERIVED / "speakers.json"
    return {(r["play"], r["label"]): r for r in json.loads(path.read_text(encoding="utf-8"))}


def resolve(ledger, reading: str, play: str, label: str) -> tuple[str, str]:
    """(分類, 正規化後のラベル) を返す。"""
    over = READINGS[reading].get((play, label))
    if over:
        if over.startswith("merge:"):
            return "actor", over.split(":", 1)[1]
        return over, label
    r = ledger[(play, label)]
    if r["class"] == "merge":
        return "actor", r["merge_into"]
    return r["class"], label


def speech_units(root, ledger, reading: str, play: str):
    """(分類, 役の集合, div要素) の列を <sp> の順に返す。

    joint(共同発話)は構成員に分解するので、役は集合で返す。
    """
    parent = {c: p for p in root.iter() for c in p}
    prev = None
    for sp in root.findall(".//t:sp", NS):
        lab = S.label_of(sp)
        if lab is None:
            if prev is None:
                raise AssertionError(f"{play}: 継承元の無い話者欠落")
            lab = prev
        prev = lab
        cls, norm = resolve(ledger, reading, play, lab)
        if cls == "joint":
            roles = set(ledger[(play, lab)]["members"])
            cls = "actor"
        else:
            roles = {norm}
        # 直近の subtype 付き div をたどる
        node, sub = sp, None
        while node in parent:
            node = parent[node]
            if node.tag.endswith("}div") and node.get("subtype"):
                sub = node.get("subtype")
                break
        yield cls, roles, id(node) if sub else None, sub


def segment(units, mode: str):
    """場面の列を返す。各場面は {roles, sp} を持つ。

    units: (分類, 役集合, div の識別子, subtype) の列
    mode: 'loose' は合唱隊発話 1 件で切る / 'strict' は合唱隊だけの div で切る
    """
    if mode == "strict":
        # 合唱隊だけで構成される div を先に求める
        by_div: dict[object, list[str]] = {}
        for cls, _roles, div, _sub in units:
            if div is not None:
                by_div.setdefault(div, []).append(cls)
        chorus_only = {d for d, cs in by_div.items() if cs and all(c == "chorus" for c in cs)}

    scenes, cur, boundaries = [], {"roles": set(), "sp": 0}, 0
    cut_subtypes = Counter()
    for cls, roles, div, sub in units:
        if mode == "loose":
            is_boundary = cls == "chorus"
        else:
            is_boundary = div in chorus_only
        if is_boundary:
            boundaries += 1
            if sub:
                cut_subtypes[sub] += 1
            if cur["sp"]:
                scenes.append(cur)
                cur = {"roles": set(), "sp": 0}
            continue
        if cls == "chorus":
            # 厳では、合唱隊だけの div に属さない合唱隊発話は境界にしない。
            # 合唱隊は俳優が演じないので場面の役にも数えない。ただし発話は消費する。
            cur["sp"] += 1
            continue
        cur["roles"] |= roles
        cur["sp"] += 1
    if cur["sp"]:
        scenes.append(cur)
    return scenes, boundaries, cut_subtypes


def main() -> int:
    ledger = load_ledger()
    out = {}
    cut_all = {"strict": Counter(), "loose": Counter()}

    for path in sorted(RAW.glob("*.perseus-grc2.xml")):
        play = path.name.split(".perseus-")[0]
        root = ET.parse(path).getroot()
        total_sp = len(root.findall(".//t:sp", NS))
        rec = {}
        for reading in ("A", "B"):
            units = list(speech_units(root, ledger, reading, play))
            for mode in ("strict", "loose"):
                scenes, nb, cuts = segment(units, mode)
                consumed = sum(s["sp"] for s in scenes) + nb
                # G-02: 発話の消化率。すべての <sp> が場面か境界のどちらかに属する。
                if consumed != total_sp:
                    raise AssertionError(
                        f"{play} {reading}/{mode}: 消化 {consumed} != 発話 {total_sp}"
                    )
                rec[f"{reading}_{mode}"] = {
                    "scenes": [{"roles": sorted(s["roles"]), "sp": s["sp"]} for s in scenes],
                    "boundaries": nb,
                }
                if reading == "A":
                    cut_all[mode] += cuts
        rec["total_sp"] = total_sp
        out[play] = rec

    DERIVED.mkdir(parents=True, exist_ok=True)
    (DERIVED / "scenes.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"45 篇の消化率 1.000(発話 {sum(v['total_sp'] for v in out.values())} 件)")
    print("\n--- 場面数と最大同席役数(読み A)---")
    print(f"{'篇':<16}{'厳:場面':>8}{'最大同席':>9}{'緩:場面':>8}{'最大同席':>9}")
    for play, v in out.items():
        st, lo = v["A_strict"], v["A_loose"]
        ms = max((len(s["roles"]) for s in st["scenes"]), default=0)
        ml = max((len(s["roles"]) for s in lo["scenes"]), default=0)
        print(f"{play:<16}{len(st['scenes']):>8}{ms:>9}{len(lo['scenes']):>8}{ml:>9}")

    print("\n--- 厳で境界になった div の subtype(語彙は判定に使っていない。結果として出る)---")
    for sub, c in cut_all["strict"].most_common(14):
        print(f"  {sub:<18} {c:>4}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
