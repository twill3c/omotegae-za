"""L5 表示用データの書き出し。

`data/derived/` は解析の生成物で、`excess.json` だけで 2.9 MB ある(『平和』の
最小解が 1,120 通りあるため)。そのまま束ねるとブラウザに配る意味の無い量になる。
ここで**表示に要るものだけ**を `src/data/` に落とす。

表示用に加工した値を検査の根拠にしない(HC-068)。ゲートの判定は
`data/derived/` の元データに対して行い、ここは見せ方だけを扱う。
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DERIVED = ROOT / "data" / "derived"
SITE = ROOT / "src" / "data"

# 邦題(手書き)。ギリシア語題は TEI ヘッダの実測値と突き合わせて確認した(2026-09-02)。
TITLES: dict[str, tuple[str, str]] = {
    "tlg0085.tlg001": ("嘆願する女たち", "アイスキュロス"),
    "tlg0085.tlg002": ("ペルシア人", "アイスキュロス"),
    "tlg0085.tlg003": ("縛られたプロメテウス", "アイスキュロス"),
    "tlg0085.tlg004": ("テーバイ攻めの七将", "アイスキュロス"),
    "tlg0085.tlg005": ("アガメムノン", "アイスキュロス"),
    "tlg0085.tlg006": ("供養する女たち", "アイスキュロス"),
    "tlg0085.tlg007": ("エウメニデス", "アイスキュロス"),
    "tlg0011.tlg001": ("トラキスの女たち", "ソポクレス"),
    "tlg0011.tlg002": ("アンティゴネ", "ソポクレス"),
    "tlg0011.tlg003": ("アイアス", "ソポクレス"),
    "tlg0011.tlg004": ("オイディプス王", "ソポクレス"),
    "tlg0011.tlg005": ("エレクトラ", "ソポクレス"),
    "tlg0011.tlg006": ("ピロクテテス", "ソポクレス"),
    "tlg0011.tlg007": ("コロノスのオイディプス", "ソポクレス"),
    "tlg0011.tlg008": ("追跡者たち(断片)", "ソポクレス"),
    "tlg0006.tlg001": ("キュクロプス", "エウリピデス"),
    "tlg0006.tlg002": ("アルケスティス", "エウリピデス"),
    "tlg0006.tlg003": ("メデイア", "エウリピデス"),
    "tlg0006.tlg004": ("ヘラクレスの子ら", "エウリピデス"),
    "tlg0006.tlg005": ("ヒッポリュトス", "エウリピデス"),
    "tlg0006.tlg006": ("アンドロマケ", "エウリピデス"),
    "tlg0006.tlg007": ("ヘカベ", "エウリピデス"),
    "tlg0006.tlg008": ("嘆願する女たち", "エウリピデス"),
    "tlg0006.tlg009": ("ヘラクレス", "エウリピデス"),
    "tlg0006.tlg010": ("イオン", "エウリピデス"),
    "tlg0006.tlg011": ("トロイアの女たち", "エウリピデス"),
    "tlg0006.tlg012": ("エレクトラ", "エウリピデス"),
    "tlg0006.tlg013": ("タウリケのイピゲネイア", "エウリピデス"),
    "tlg0006.tlg014": ("ヘレネ", "エウリピデス"),
    "tlg0006.tlg015": ("フェニキアの女たち", "エウリピデス"),
    "tlg0006.tlg016": ("オレステス", "エウリピデス"),
    "tlg0006.tlg017": ("バッコスの信女", "エウリピデス"),
    "tlg0006.tlg018": ("アウリスのイピゲネイア", "エウリピデス"),
    "tlg0006.tlg019": ("レソス", "エウリピデス"),
    "tlg0019.tlg001": ("アカルナイの人々", "アリストパネス"),
    "tlg0019.tlg002": ("騎士", "アリストパネス"),
    "tlg0019.tlg003": ("雲", "アリストパネス"),
    "tlg0019.tlg004": ("蜂", "アリストパネス"),
    "tlg0019.tlg005": ("平和", "アリストパネス"),
    "tlg0019.tlg006": ("鳥", "アリストパネス"),
    "tlg0019.tlg007": ("リュシストラテ", "アリストパネス"),
    "tlg0019.tlg008": ("女だけの祭", "アリストパネス"),
    "tlg0019.tlg009": ("蛙", "アリストパネス"),
    "tlg0019.tlg010": ("女の議会", "アリストパネス"),
    "tlg0019.tlg011": ("福の神", "アリストパネス"),
}

GENRE = {"tlg0085": "悲劇", "tlg0011": "悲劇", "tlg0006": "悲劇", "tlg0019": "喜劇"}
ORDER = ["tlg0085", "tlg0011", "tlg0006", "tlg0019"]

# 最小解が数百通りある篇があるので、表示はここまでで打ち切る。
# 打ち切ったことは必ず画面に出す(黙って切らない)。
MAX_CANDIDATES = 12


def _edges(scenes: list[dict]) -> set[frozenset[str]]:
    """場面から辺を作り直す。coloring.json は本数しか持たないので、ここで再計算する。"""
    from itertools import combinations

    out: set[frozenset[str]] = set()
    for s in scenes:
        for a, b in combinations(sorted(s["roles"]), 2):
            out.add(frozenset((a, b)))
    return out


def main() -> int:
    inv = {r["file"].split(".perseus-")[0]: r for r in json.loads((DERIVED / "inventory.json").read_text(encoding="utf-8"))}
    col = json.loads((DERIVED / "coloring.json").read_text(encoding="utf-8"))
    scn = json.loads((DERIVED / "scenes.json").read_text(encoding="utf-8"))
    exc = json.loads((DERIVED / "excess.json").read_text(encoding="utf-8"))
    ctl = json.loads((DERIVED / "control.json").read_text(encoding="utf-8"))
    led = json.loads((DERIVED / "speakers.json").read_text(encoding="utf-8"))

    reviews: dict[str, list[str]] = {}
    for r in led:
        if r["class"] == "review":
            reviews.setdefault(r["play"], []).append(r["label"])

    index = []
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "play").mkdir(exist_ok=True)

    missing = set(inv) - set(TITLES)
    if missing:
        raise AssertionError(f"邦題の無い篇がある: {sorted(missing)}")

    for pid in sorted(inv, key=lambda p: (ORDER.index(p.split(".")[0]), p)):
        i = inv[pid]
        ja, author = TITLES[pid]
        group = pid.split(".")[0]
        ed = i["edition"]
        summary = {
            "id": pid,
            "ja": ja,
            "grc": i["title_grc"] or i["title"],
            "author": author,
            "genre": GENRE[group],
            "lines": i["lines"],
            "sp": i["sp"],
            "chi": {m: col[pid][m]["chi"] for m in col[pid]},
            "vertices": col[pid]["A_loose"]["vertices"],
            "scenes": {
                "strict": len(scn[pid]["A_strict"]["scenes"]),
                "loose": len(scn[pid]["A_loose"]["scenes"]),
            },
        }
        index.append(summary)

        detail = {
            **summary,
            "urn": i["urn"],
            "edition": {
                "editor": ed.get("editor", ""),
                "title": ed.get("title", ""),
                "date": ed.get("date", ""),
                "ref": ed.get("ref", ""),
            },
            "cast": {m: col[pid][m]["cast"] for m in col[pid]},
            "edge_count": {m: col[pid][m]["edges"] for m in col[pid]},
            "edges": {
                m: sorted(sorted(e) for e in _edges(scn[pid][m]["scenes"]))
                for m in ("A_strict", "A_loose")
            },
            # 帯には**境界(合唱歌)も描く**。場面だけを並べると合唱歌の位置が
            # 見えず、凡例の「合唱隊のみ」が図に存在しない色を指すことになる
            # (L7 の実ブラウザ検品で発見)。
            "band": {m: scn[pid][m]["band"] for m in ("A_strict", "A_loose")},
            "boundaries": {m: scn[pid][m]["boundaries"] for m in ("A_strict", "A_loose")},
            "excess": {
                m: {
                    "chi": exc[pid][m]["chi"],
                    "excess": exc[pid][m]["excess"],
                    "k": exc[pid][m].get("k"),
                    "union": exc[pid][m].get("candidate_union", []),
                    "is_clique": exc[pid][m].get("union_is_clique", False),
                    "host_scenes": exc[pid][m].get("host_scenes", []),
                    "candidates": exc[pid][m]["candidates"][:MAX_CANDIDATES],
                    "candidates_total": len(exc[pid][m]["candidates"]),
                }
                for m in ("A_strict", "A_loose")
            },
            "control": ctl[pid],
            "review_labels": sorted(reviews.get(pid, [])),
        }
        (SITE / "play" / f"{pid}.json").write_text(
            json.dumps(detail, ensure_ascii=False), encoding="utf-8"
        )

    (SITE / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    total = sum(p.stat().st_size for p in SITE.rglob("*.json"))
    print(f"{len(index)} 篇  合計 {total / 1024:.1f} KB")
    biggest = sorted(SITE.rglob("*.json"), key=lambda p: -p.stat().st_size)[:3]
    for p in biggest:
        print(f"  {p.stat().st_size / 1024:7.1f} KB  {p.relative_to(SITE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
