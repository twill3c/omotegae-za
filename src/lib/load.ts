import { readFileSync } from "node:fs";
import path from "node:path";
import type { PlayDetail } from "./site";

/**
 * 篇ごとの詳細をビルド時に読む。
 *
 * `src/data/play/*.json` を静的 import すると 45 ファイルが常に束ねられるので、
 * ファイルシステムから読む。静的書き出し(output: "export")なので、
 * この関数はビルド時にしか動かない —— 実行時にファイルを読む経路は残らない。
 */
export function loadPlay(id: string): PlayDetail {
  if (!/^tlg\d{4}\.tlg\d{3}$/.test(id)) {
    throw new Error(`篇の識別子が不正: ${id}`);
  }
  const file = path.join(process.cwd(), "src", "data", "play", `${id}.json`);
  return JSON.parse(readFileSync(file, "utf-8")) as PlayDetail;
}

export type ReaderRow = { lines: number; ja: number };

/**
 * 和訳の充填状況。
 *
 * リーダーの JSON は 45 篇で 8.75MB あるので、トップページのために全部読まない。
 * `build_reader.py` が書く集計(篇 → 行数・訳出数)だけを読む。
 * この数はパイプラインの実測であって、手で書いた数ではない。
 */
export function loadReaderReport(): Record<string, ReaderRow> {
  const file = path.join(process.cwd(), "data", "derived", "reader_report.json");
  return JSON.parse(readFileSync(file, "utf-8")) as Record<string, ReaderRow>;
}
