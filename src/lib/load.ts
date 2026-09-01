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
