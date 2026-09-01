# データと和訳のライセンス — CC BY-SA 4.0

本ディレクトリ(`data/`)以下のすべてのファイル、および本プロジェクトが生成する
**日本語訳文**は、**Creative Commons Attribution-ShareAlike 4.0 International
(CC BY-SA 4.0)** で提供する。

リポジトリのルートにある `LICENSE`(MIT)は**コードにのみ**適用される。
`data/` と和訳には適用されない。

## 原典の出所

`data/raw/` の 45 ファイルは Perseus Digital Library の
[`PerseusDL/canonical-greekLit`](https://github.com/PerseusDL/canonical-greekLit)
から採録した TEI XML の**原本**であり、改変していない(SPEC N-04)。

> Tufts University holds the overall copyright to the Perseus Digital Library.
> Unless otherwise indicated, all contents of that repository are licensed under a
> Creative Commons Attribution-ShareAlike 4.0 International License.

## 継承(ShareAlike)について

本プロジェクトの和訳は、Perseus のギリシア語校訂本文に基づく**二次的著作物**である。
したがって CC BY-SA 4.0 の継承条件により、和訳も同じ条件で提供する。
和訳を再配布・改変する者も、同じ条件で提供しなければならない。

## 帰属表示

各篇のページに、次の三つを表示する(SPEC G-00)。

1. Perseus Digital Library, Tufts University(および当該テキストの CTS URN)
2. その篇の**底本**(校訂者名・書名・刊年)
3. CC BY-SA 4.0 へのリンク

底本は篇ごとに異なる。全 45 篇の内訳(実測 2026-09-02・TEI ヘッダの `sourceDesc` より):

| 作家 | 篇数 | 校訂者 | 書名 | 刊年 |
|---|---:|---|---|---|
| アイスキュロス | 7 | Herbert Weir Smyth | Aeschylus | 1922 / 1926 |
| ソポクレス | 7 | Francis Storr | Sophocles | 1912 / 1913 |
| ソポクレス(追跡者たち) | 1 | Arthur S. Hunt | Oxyrhynchus Papyri | 1912 |
| エウリピデス | 19 | Gilbert Murray | Euripidis Fabulae | 1902 / 1913 |
| アリストパネス | 11 | F. W. Hall / William M. Geldart | Aristophanis Comoediae | 1906 / 1907 |

篇ごとの正確な対応は `data/derived/inventory.json` の `edition` に持つ。
