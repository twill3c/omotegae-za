"""L0 素材台帳 — Perseus canonical-greekLit の TEI を全数走査して実測値を出す。

grep では属性の並び順に依存して静かに取りこぼす(2026-09-01 に max-n の集計が
エウリピデス/アリストパネスで 0 になった)。ここでは XML として読む。

HC-075 に従い、仮定は書いた場所で検算する。仮定が外れたら黙って違う結果を出さず、
その場で例外にして止める。
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

TEI = "http://www.tei-c.org/ns/1.0"
NS = {"t": TEI}

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"
DERIVED = Path(__file__).resolve().parent.parent / "data" / "derived"

# CTS textgroup → 作家名。Perseus の URN 体系(TLG 著者番号)。
GROUPS = {
    "tlg0085": "Aeschylus",
    "tlg0011": "Sophocles",
    "tlg0006": "Euripides",
    "tlg0019": "Aristophanes",
}

NUMERIC_N = re.compile(r"^\d+$")


def _text(el) -> str:
    """要素以下の全テキストを連結して正規化する。"""
    if el is None:
        return ""
    return " ".join("".join(el.itertext()).split())


def _first(root, path: str):
    return root.find(path, NS)


def scan(path: Path) -> dict:
    root = ET.parse(path).getroot()

    if not root.tag.endswith("}TEI"):
        raise AssertionError(f"{path.name}: 根要素が TEI ではない: {root.tag}")

    stem = path.name.split(".perseus-")[0]
    group, work = stem.split(".")
    if group not in GROUPS:
        raise AssertionError(f"{path.name}: 未知の textgroup {group}")

    # --- 題名 ---------------------------------------------------------------
    titles = _first(root, ".//t:fileDesc/t:titleStmt")
    title_grc = ""
    title_any = ""
    for el in titles.findall("t:title", NS):
        s = _text(el)
        if el.get("{http://www.w3.org/XML/1998/namespace}lang") == "grc":
            title_grc = s
        elif not title_any:
            title_any = s

    # --- 底本(sourceDesc)— 権利表示 G-00 の材料 ---------------------------
    src = _first(root, ".//t:sourceDesc//t:monogr")
    edition = {}
    if src is not None:
        edition = {
            "title": _text(_first(src, "t:title")),
            "editor": " / ".join(_text(e) for e in src.findall("t:editor", NS)),
            "publisher": " / ".join(_text(e) for e in src.findall(".//t:publisher", NS)),
            "date": _text(_first(src, ".//t:date")),
        }
    ref = _first(root, ".//t:sourceDesc//t:ref")
    if ref is not None:
        edition["ref"] = ref.get("target", "")

    # --- 行 -----------------------------------------------------------------
    lines = root.findall(".//t:l", NS)
    n_values = [el.get("n") for el in lines]

    # 仮定: すべての <l> は @n を持つ。持たない行があれば行番号突合が成立しない。
    missing_n = sum(1 for v in n_values if v is None)
    if missing_n:
        raise AssertionError(f"{path.name}: @n を持たない <l> が {missing_n} 件")

    numeric = [int(v) for v in n_values if NUMERIC_N.match(v)]
    non_numeric = sorted({v for v in n_values if not NUMERIC_N.match(v)})

    l_attrs = Counter()
    for el in lines:
        l_attrs.update(el.attrib.keys())

    part_values = Counter(el.get("part") for el in lines if el.get("part"))

    # --- 発話 ---------------------------------------------------------------
    sps = root.findall(".//t:sp", NS)
    speakers_text: list[str] = []
    speakers_id: list[str] = []
    sp_without_speaker = 0
    for sp in sps:
        spk = sp.find("t:speaker", NS)
        if spk is None:
            sp_without_speaker += 1
            continue
        ident = spk.get("n")
        body = _text(spk)
        if ident:
            speakers_id.append(ident.lstrip("#"))
        elif body:
            speakers_text.append(body)
        else:
            sp_without_speaker += 1

    if speakers_text and speakers_id:
        form = "mixed"
    elif speakers_id:
        form = "id"          # <speaker n="#Διόνυσος"/>
    elif speakers_text:
        form = "text"        # <speaker>Ἀγαμέμνων</speaker>
    else:
        form = "none"

    names = Counter(speakers_text or speakers_id)
    # καὶ を含む話者名 = 複数人の共同発話。「一発話 = 一話者」の前提が崩れる箇所。
    joint = {k: v for k, v in names.items() if " καὶ " in f" {k} "}

    return {
        "file": path.name,
        "urn": f"urn:cts:greekLit:{group}.{work}.perseus-grc2",
        "group": group,
        "author": GROUPS[group],
        "work": work,
        "title_grc": title_grc,
        "title": title_any,
        "edition": edition,
        "lines": len(lines),
        "line_n_max": max(numeric) if numeric else None,
        "line_n_distinct": len(set(n_values)),
        "line_n_non_numeric": non_numeric,
        "line_attrs": dict(l_attrs),
        "antilabe_parts": dict(part_values),
        "sp": len(sps),
        "speaker_form": form,
        "speakers": len(names),
        "speaker_names": sorted(names),
        "joint_speakers": joint,
        "sp_without_speaker": sp_without_speaker,
    }


def main() -> int:
    files = sorted(RAW.glob("*.perseus-grc2.xml"))
    if len(files) != 45:
        raise AssertionError(f"grc2 が 45 篇そろっていない: {len(files)} 件")

    rows = [scan(f) for f in files]
    DERIVED.mkdir(parents=True, exist_ok=True)
    (DERIVED / "inventory.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    hdr = f"{'urn':<34}{'題名':<26}{'行':>6}{'n最大':>7}{'差':>5}{'発話':>6}{'話者':>5}  形式"
    print(hdr)
    print("-" * len(hdr))
    for r in rows:
        mx = r["line_n_max"]
        gap = "" if mx is None else mx - r["lines"]
        print(
            f"{r['group']}.{r['work']:<26}{(r['title_grc'] or r['title'])[:24]:<26}"
            f"{r['lines']:>6}{mx if mx is not None else '-':>7}{gap:>5}"
            f"{r['sp']:>6}{r['speakers']:>5}  {r['speaker_form']}"
        )

    print()
    for g, name in GROUPS.items():
        sub = [r for r in rows if r["group"] == g]
        print(
            f"{name:<14} {len(sub):>2}篇  行 {sum(r['lines'] for r in sub):>6}  "
            f"発話 {sum(r['sp'] for r in sub):>5}  "
            f"antilabe {sum(sum(r['antilabe_parts'].values()) for r in sub):>5}"
        )
    print(
        f"{'計':<14} {len(rows):>2}篇  行 {sum(r['lines'] for r in rows):>6}  "
        f"発話 {sum(r['sp'] for r in rows):>5}  "
        f"antilabe {sum(sum(r['antilabe_parts'].values()) for r in rows):>5}"
    )

    print("\n--- 話者マークアップの流儀 ---")
    for form, cnt in Counter(r["speaker_form"] for r in rows).most_common():
        who = [f"{r['group']}.{r['work']}" for r in rows if r["speaker_form"] == form]
        print(f"  {form:<6} {cnt:>2}篇  {' '.join(who[:6])}{' …' if len(who) > 6 else ''}")

    print("\n--- 共同発話(一発話 = 一話者 が崩れる箇所) ---")
    any_joint = False
    for r in rows:
        for k, v in r["joint_speakers"].items():
            any_joint = True
            print(f"  {r['group']}.{r['work']} {r['title_grc'][:16]:<18} {k}  ×{v}")
    if not any_joint:
        print("  なし")

    print("\n--- 行番号が数値でない篇 ---")
    odd = [r for r in rows if r["line_n_non_numeric"]]
    for r in odd:
        vals = r["line_n_non_numeric"]
        print(f"  {r['group']}.{r['work']}  {len(vals)}種  例: {vals[:8]}")
    if not odd:
        print("  なし")

    print("\n--- <sp> に <speaker> が無い箇所 ---")
    miss = [r for r in rows if r["sp_without_speaker"]]
    for r in miss:
        print(f"  {r['group']}.{r['work']}  {r['sp_without_speaker']} 件")
    if not miss:
        print("  なし")

    return 0


if __name__ == "__main__":
    sys.exit(main())
