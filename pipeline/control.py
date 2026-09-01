"""L4 置換対照 —— χ の小ささは劇の設計か、役数の少なさか。

## 帰無仮説

「χ ≤ 3 の悲劇が多い」のは、単にその篇の**役数が少ない**からかもしれない。
役が 5 つしかなければ χ は高々 5 で、3 に収まっても不思議はない。
これを排除しないと、目玉は何も主張していないに等しい。

## 偽の劇の作り方

発話の**並びと場面の境界はそのまま**にして、**俳優の発話に貼られた役のラベルだけを
篇内で無作為に置換する**。

置換で保たれるもの:
  - 発話の総数、場面の数と大きさ、境界の位置
  - 異なり役数、各役の発話回数の**多重集合**

置換で壊れるもの:
  - どの役がどの場面に集まるか(= 兼ねられるかどうかの構造)

したがって「実劇の χ が偽の劇より有意に小さい」なら、その小ささは
役数でも発話数でも場面数でもなく、**役の配置**に由来する。

## 有意性

seed 固定・2,000 回。片側 p 値は (χ_null <= χ_obs の回数 + 1) / (回数 + 1)。
+1 は置換検定の標準的な補正で、p = 0 を出さないため。
"""

from __future__ import annotations

import json
import random
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import coloring as C  # noqa: E402
import scenes as SC  # noqa: E402
import speakers as S  # noqa: E402

NS = {"t": "http://www.tei-c.org/ns/1.0"}
SEED = 20260902
TRIALS = 2000


def chi_of(scene_list: list[dict]) -> int:
    verts, edges = C.build_graph(scene_list)
    adj = C.adjacency(verts, edges)
    lower = max((len(s["roles"]) for s in scene_list), default=0)
    return C.chromatic(adj, lower)[0]


def permuted_scenes(units, mode: str, rng: random.Random) -> list[dict]:
    """俳優発話の役ラベルだけを置換してから場面に切り直す。"""
    labels = [roles for cls, roles, _d, _s in units if cls == "actor"]
    flat = [next(iter(r)) if len(r) == 1 else None for r in labels]
    # 共同発話(役が 2 つ以上)はそのまま動かさない —— 置換の対象は単独役のラベル。
    movable = [i for i, f in enumerate(flat) if f is not None]
    vals = [flat[i] for i in movable]
    rng.shuffle(vals)
    for i, v in zip(movable, vals):
        flat[i] = v

    shuffled = []
    k = 0
    for cls, roles, d, sub in units:
        if cls == "actor":
            shuffled.append((cls, {flat[k]} if flat[k] else roles, d, sub))
            k += 1
        else:
            shuffled.append((cls, roles, d, sub))
    scene_list, _nb, _c = SC.segment(shuffled, mode)
    return [{"roles": sorted(s["roles"]), "sp": s["sp"]} for s in scene_list]


def main() -> int:
    ledger = SC.load_ledger()
    observed = json.loads(
        (ROOT / "data" / "derived" / "coloring.json").read_text(encoding="utf-8")
    )
    out: dict[str, dict] = {}

    for path in sorted((ROOT / "data" / "raw").glob("*.perseus-grc2.xml")):
        play = path.name.split(".perseus-")[0]
        root = ET.parse(path).getroot()
        units = list(SC.speech_units(root, ledger, "A", play))
        out[play] = {}
        for mode in ("strict", "loose"):
            obs = observed[play][f"A_{mode}"]["chi"]
            rng = random.Random(SEED)
            null = []
            for _ in range(TRIALS):
                null.append(chi_of(permuted_scenes(units, mode, rng)))
            le = sum(1 for x in null if x <= obs)
            out[play][mode] = {
                "observed": obs,
                "null_mean": round(sum(null) / len(null), 3),
                "null_min": min(null),
                "null_max": max(null),
                "p": round((le + 1) / (TRIALS + 1), 5),
                "trials": TRIALS,
                "seed": SEED,
            }
        print(
            f"{play:<16} 厳 obs {out[play]['strict']['observed']:>2} "
            f"vs 帰無 {out[play]['strict']['null_mean']:>6}  p={out[play]['strict']['p']:<8} "
            f"緩 obs {out[play]['loose']['observed']:>2} "
            f"vs 帰無 {out[play]['loose']['null_mean']:>6}  p={out[play]['loose']['p']}",
            flush=True,
        )

    (ROOT / "data" / "derived" / "control.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    trag = [p for p in out if p.split(".")[0] in {"tlg0085", "tlg0011", "tlg0006"}]
    for mode in ("strict", "loose"):
        sig = sum(1 for p in trag if out[p][mode]["p"] < 0.01)
        print(f"\n{mode}: 悲劇 {sig}/{len(trag)} 篇で p < 0.01")
    return 0


if __name__ == "__main__":
    sys.exit(main())
