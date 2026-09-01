"""L5 出荷物の検査。**書き出した HTML を読む** —— ソースではなく成果物を見る。

satei-kobo HC-001「数は正しく図だけが嘘」を踏まえ、
ページに出ている数が派生データと一致することを機械的に突き合わせる(G-09)。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "out"


def _need_build():
    if not (OUT / "index.html").exists():
        pytest.skip("先に next build を実行する(out/ が無い)")


@pytest.fixture(scope="module")
def plays() -> list[dict]:
    return json.loads((ROOT / "src" / "data" / "index.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def coloring() -> dict:
    return json.loads((ROOT / "data" / "derived" / "coloring.json").read_text(encoding="utf-8"))


@pytest.mark.validation
def test_N01_サーバ関数もcronも持たない():
    """静的書き出しのみ。課金経路をひとつも作らない。"""
    cfg = (ROOT / "next.config.ts").read_text(encoding="utf-8")
    assert 'output: "export"' in cfg
    assert not (ROOT / "vercel.json").exists() or "crons" not in (
        ROOT / "vercel.json"
    ).read_text(encoding="utf-8")
    # API ルート・サーバアクションの入口が無いこと
    assert not list((ROOT / "src" / "app").rglob("route.ts"))
    assert not list((ROOT / "src" / "app").rglob("route.tsx"))
    for p in (ROOT / "src").rglob("*.ts*"):
        assert '"use server"' not in p.read_text(encoding="utf-8"), p


@pytest.mark.validation
def test_45篇すべてのページが書き出されている(plays):
    _need_build()
    missing = [p["id"] for p in plays if not (OUT / "play" / p["id"] / "index.html").exists()]
    assert not missing, missing
    assert len(plays) == 45


@pytest.mark.validation
def test_G00_全篇に底本と権利表示がある(plays):
    """欠けたまま出荷しない。CC BY-SA 4.0 は継承条件付きなので帰属表示は義務である。"""
    _need_build()
    inv = {
        r["file"].split(".perseus-")[0]: r
        for r in json.loads((ROOT / "data" / "derived" / "inventory.json").read_text(encoding="utf-8"))
    }
    for p in plays:
        html = (OUT / "play" / p["id"] / "index.html").read_text(encoding="utf-8")
        assert "Perseus Digital Library" in html, p["id"]
        assert "CC BY-SA 4.0" in html, p["id"]
        assert p["id"] in html, p["id"]  # CTS URN
        editor = inv[p["id"]]["edition"].get("editor", "")
        if editor:
            # 姓だけでも出ていること(氏名の表記は HTML 側で分割されうる)
            assert editor.split()[-1] in html, (p["id"], editor)


@pytest.mark.validation
def test_G06_作家間比較に交絡の注記がある():
    """注記の無い作家間比較を 0 件にする(SPEC G-06)。

    作家名が 4 つとも並ぶページには、校訂者交絡の注記が必ず付く。
    """
    _need_build()
    authors = ["アイスキュロス", "ソポクレス", "エウリピデス", "アリストパネス"]
    for html_path in OUT.rglob("index.html"):
        text = _visible(html_path)
        if all(a in text for a in authors):
            assert "校訂者" in text, html_path
            assert ("分離できない" in text) or ("交絡" in text), html_path


def _visible(html_path: Path) -> str:
    """**見える本文**だけを取り出す。

    生の HTML で判定すると、`<script>` に埋め込まれた RSC ペイロード
    (index.json の全篇分が入る)が拾われ、何も表示していない 404 ページまで
    「四作家を並べている」と判定されてしまう。実測 2026-09-02 に踏んだ。
    """
    html = html_path.read_text(encoding="utf-8")
    html = re.sub(r"<script\b.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style\b.*?</style>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


@pytest.mark.validation
def test_G09_ページのχが派生データと一致する(plays, coloring):
    """**図だけが嘘をつく**のを防ぐ。各篇のページに出ている χ を派生データと突き合わせる。"""
    _need_build()
    for p in plays:
        html = (OUT / "play" / p["id"] / "index.html").read_text(encoding="utf-8")
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text)
        loose = coloring[p["id"]]["A_loose"]["chi"]
        strict = coloring[p["id"]]["A_strict"]["chi"]
        assert p["chi"]["A_loose"] == loose and p["chi"]["A_strict"] == strict, p["id"]
        # 「要る俳優 χ <loose> (緩) / <strict> (厳)」の並びが本文に出ていること
        assert re.search(rf"{loose}\s*(?:(緩)|(\(緩\)))\s*/\s*{strict}\s*", text), (
            p["id"],
            loose,
            strict,
        )


@pytest.mark.validation
def test_打ち切った件数は画面に出す(plays):
    """最小解を 12 通りで打ち切っている篇では、総数を明示する(黙って切らない)。"""
    _need_build()
    for p in plays:
        d = json.loads((ROOT / "src" / "data" / "play" / f"{p['id']}.json").read_text(encoding="utf-8"))
        ex = d["excess"]["A_loose"]
        if ex["candidates_total"] > len(ex["candidates"]):
            html = (OUT / "play" / p["id"] / "index.html").read_text(encoding="utf-8")
            assert str(ex["candidates_total"]) in html, p["id"]


@pytest.mark.validation
def test_落ちたゲートが方法のページに書かれている():
    """通らなかったことを消さない。"""
    _need_build()
    html = (OUT / "method" / "index.html").read_text(encoding="utf-8")
    assert "不通過" in html
    assert "落ちた予測" in html or "落ちた" in html


@pytest.mark.validation
def test_日本語本文にキリル文字が混じらない():
    """[[fleet-cyrillic-leak]] — 字形が似て目視では気づけない(SPEC N-03)。

    ギリシア文字は原文の役名として意図的に使うので対象外にする。
    """
    _need_build()
    cyr = re.compile(r"[Ѐ-ӿ]")
    bad = []
    for html_path in OUT.rglob("*.html"):
        for m in cyr.finditer(html_path.read_text(encoding="utf-8")):
            bad.append((html_path.name, m.group()))
    assert not bad, bad[:10]
