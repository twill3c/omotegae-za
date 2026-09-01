import Link from "next/link";
import { notFound } from "next/navigation";
import { readFileSync } from "node:fs";
import path from "node:path";
import { PLAYS } from "@/lib/site";

export function generateStaticParams() {
  return PLAYS.map((p) => ({ id: p.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const p = PLAYS.find((x) => x.id === id);
  return { title: p ? `${p.ja} 本文 — 面替え座` : "面替え座" };
}

interface Speech {
  who: string;
  cls: string;
  inherited: boolean;
  lines: [string, string][];
}

interface Reader {
  id: string;
  speeches: Speech[];
  en: {
    version: string;
    others: string[];
    translator: string;
    source: string;
    date: string;
    anchored: Record<string, string>;
    stages: Record<string, string[]>;
    notes_dropped: number;
  } | null;
  align: { matched: number; unmatched: number; blocks: number };
}

/**
 * 錨のある行で束に切る。
 *
 * 散文訳は数行をひとまとめにするので、一行ごとの格子に載せると
 * **英訳の高さが原文の行間を押し広げ、縦の間隔がばらつく**(L7 の目視で発見)。
 * 錨から次の錨までを一束にすれば、左右の高さが自然に釣り合う。
 * 対応の正しさは変わらない —— 束の先頭行が、その英訳が指す行である。
 */
function chunk(
  lines: [string, string][],
  anchored: Record<string, string>,
  stages: Record<string, string[]>,
): { lines: [string, string][]; en: string; stages: string[] }[] {
  const out: { lines: [string, string][]; en: string; stages: string[] }[] = [];
  for (const ln of lines) {
    const [n] = ln;
    const hasAnchor = anchored[n] !== undefined || stages[n] !== undefined;
    if (out.length === 0 || hasAnchor) {
      out.push({ lines: [ln], en: anchored[n] ?? "", stages: stages[n] ?? [] });
    } else {
      out[out.length - 1].lines.push(ln);
    }
  }
  return out;
}

function loadReader(id: string): Reader {
  if (!/^tlg\d{4}\.tlg\d{3}$/.test(id)) throw new Error(`不正な識別子: ${id}`);
  const f = path.join(process.cwd(), "src", "data", "reader", `${id}.json`);
  return JSON.parse(readFileSync(f, "utf-8")) as Reader;
}

export default async function Read({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const meta = PLAYS.find((p) => p.id === id);
  if (!meta) notFound();
  const r = loadReader(id);
  const anchored = r.en?.anchored ?? {};
  const stages = r.en?.stages ?? {};

  return (
    <main className="wrap" style={{ paddingTop: "2rem" }}>
      <p style={{ color: "var(--ink-faint)", fontSize: ".82rem", margin: 0 }}>
        <Link href={`/play/${id}/`} prefetch={false}>
          {meta.ja}
        </Link>{" "}
        ・ {meta.author}
      </p>
      <h1>
        {meta.ja} <span className="grc" style={{ fontSize: "1.1rem", color: "var(--ink-faint)" }}>{meta.grc}</span>
      </h1>
      <p className="lede">
        Perseus のギリシア語校訂本文を<b>行番号のまま</b>読む。
        左が原文、右が英訳。話者名は原文のラベルをそのまま出している。
      </p>

      {r.en ? (
        <div className="note">
          <strong>英訳:</strong> {r.en.translator}『{r.en.source}』{r.en.date}
          {r.en.others.length > 0 && <>(他に {r.en.others.join("・")} の訳もある)</>}
          <br />
          散文訳は数行をひとまとめにするので、右の塊は<b>その塊が始まる行</b>に置いてある。
          <br />
          対応づけ: 錨 {r.align.blocks.toLocaleString()} 件のうち
          <b>{r.align.unmatched} 件は原文の行番号に無い</b>ため置いていない
          {r.align.unmatched > 0 && (
            <>
              (
              {meta.author === "ソポクレス"
                ? "原文は Storr、英訳は Jebb の校訂で版が違う"
                : "英訳側の行番号の誤植を含む"}
              )
            </>
          )}
          。近い行へ寄せることはしていない。
          {r.en.notes_dropped > 0 && (
            <>
              <br />
              訳者の脚注 {r.en.notes_dropped} 件は本文から外した(そのまま繋ぐと訳文と注釈の区別が付かなくなる)。
            </>
          )}
          {Object.keys(stages).length > 0 && (
            <>
              {" "}
              ト書きは<b>訳者が補ったもの</b>で原文には無い。区別できる形で示す。
            </>
          )}
        </div>
      ) : (
        <div className="note note--warn">
          <strong>この篇の英訳は Perseus に無い。</strong>
          アリストパネスは 11 篇中 2 篇(雲・鳥)しか英訳が収録されていない。
          埋めずに空欄で出す。
        </div>
      )}

      <div className="reader">
        {r.speeches.map((s, i) => (
          <section key={i} className={"sp" + (s.cls === "chorus" ? " sp--chorus" : "")}>
            <h2 className="sp__who grc">
              {s.who}
              {s.inherited && (
                <span className="sp__note" title="原文に話者名が無く、直前の話者を継いだ箇所">
                  (継承)
                </span>
              )}
            </h2>
            {chunk(s.lines, anchored, stages).map((c, k) => (
              <div className="chunk" key={k}>
                <div className="chunk__grc">
                  {c.lines.map(([n, t]) => (
                    <div className="ln" key={n} id={`l${n}`}>
                      <span className="ln__n">{/\d0$|\d5$/.test(n) || n === "1" ? n : ""}</span>
                      <span className="ln__grc grc">{t}</span>
                    </div>
                  ))}
                </div>
                <div className="chunk__en">
                  {c.stages.map((x, j) => (
                    <span className="stage" key={j}>
                      〔{x}〕
                    </span>
                  ))}
                  {c.en}
                </div>
              </div>
            ))}
          </section>
        ))}
      </div>

      <p style={{ marginTop: "2.5rem", fontSize: ".82rem", color: "var(--ink-faint)" }}>
        本文: Perseus Digital Library, Tufts University ・ CC BY-SA 4.0。
        <code>data/raw</code> は原本のまま据え置いており、本文に手を入れていない。
      </p>
    </main>
  );
}
