import Link from "next/link";
import { notFound } from "next/navigation";
import { Band } from "@/components/Band";
import { ACTOR_COLORS, ConflictGraph } from "@/components/ConflictGraph";
import { loadPlay } from "@/lib/load";
import { CLAIMED_ACTORS, PLAYS } from "@/lib/site";

export function generateStaticParams() {
  return PLAYS.map((p) => ({ id: p.id }));
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const p = PLAYS.find((x) => x.id === id);
  return { title: p ? `${p.ja} — 面替え座` : "面替え座" };
}

export default async function PlayPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!PLAYS.some((p) => p.id === id)) notFound();
  const d = loadPlay(id);
  const i = PLAYS.findIndex((p) => p.id === id);
  const prev = PLAYS[i - 1];
  const next = PLAYS[i + 1];

  const over = d.chi.A_loose > CLAIMED_ACTORS;
  const ex = d.excess.A_loose;
  const ctlLoose = d.control.loose;

  return (
    <main className="wrap" style={{ paddingTop: "2rem" }}>
      <p style={{ color: "var(--ink-faint)", fontSize: ".82rem", margin: 0 }}>
        {d.author} ・ {d.genre}
      </p>
      <h1>
        {d.ja} <span className="grc" style={{ fontSize: "1.1rem", color: "var(--ink-faint)" }}>{d.grc}</span>
      </h1>

      <dl className="kv" style={{ marginTop: "1rem" }}>
        <dt>行</dt>
        <dd>{d.lines.toLocaleString()}</dd>
        <dt>発話</dt>
        <dd>{d.sp.toLocaleString()}</dd>
        <dt>語る役</dt>
        <dd>{d.vertices}(合唱隊を除く)</dd>
        <dt>要る俳優 χ</dt>
        <dd>
          <b style={{ color: over ? "var(--tone-many)" : "var(--ink)" }}>{d.chi.A_loose}</b>(緩)
          {" / "}
          {d.chi.A_strict}(厳)
        </dd>
        <dt>本文</dt>
        <dd>
          <Link href={`/play/${d.id}/read/`} prefetch={false}>
            原文を行番号のまま読む →
          </Link>
        </dd>
      </dl>

      <h2>骨格帯</h2>
      <p className="lede">
        幅は発話数に比例。場面は<b>そこに居合わせる役の数</b>で塗り、
        合唱歌は灰色にした。灰色の位置で登退場が起こりうる。
      </p>
      <h3>緩 — 合唱隊の発話 1 件で切る</h3>
      <Band items={d.band.A_loose} height={26} />
      <p style={{ fontSize: ".8rem", color: "var(--ink-faint)" }}>
        {d.scenes.loose} 場面 / 合唱歌の区間 {d.boundaries.A_loose} 発話ぶん
      </p>
      <h3>厳 — 合唱隊だけの div でのみ切る</h3>
      <Band items={d.band.A_strict} height={26} />
      <p style={{ fontSize: ".8rem", color: "var(--ink-faint)" }}>
        {d.scenes.strict} 場面 / 合唱歌の区間 {d.boundaries.A_strict} 発話ぶん。
        厳は場面を併合するので衝突が増え、χ は減らない —— <b>反証側の測り方</b>である。
      </p>

      <h2>配役盤</h2>
      <p className="lede">
        頂点は役、辺は「同じ場面に居合わせるので兼ねられない」関係。
        頂点の色は割り当てられた俳優で、<b>同色の頂点は辺で結ばれていない</b>。
        彩色は厳密解で、Python と TypeScript の二実装が一致したものである。
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,18rem)", gap: "1.5rem", alignItems: "start" }}>
        <ConflictGraph
          vertices={Object.values(d.cast.A_loose).flat().sort()}
          edges={d.edges.A_loose}
          cast={d.cast.A_loose}
        />
        <div>
          <h3 style={{ marginTop: 0 }}>面替えスケジュール(緩)</h3>
          <ul className="castlist">
            {Object.entries(d.cast.A_loose).map(([c, roles]) => (
              <li key={c}>
                <b style={{ color: ACTOR_COLORS[Number(c) % ACTOR_COLORS.length] }}>
                  俳優 {Number(c) + 1}
                </b>
                <span className="grc">{roles.join(" ・ ")}</span>
              </li>
            ))}
          </ul>
          <p style={{ fontSize: ".78rem", color: "var(--ink-faint)" }}>
            辺 {d.edge_count.A_loose} 本。<b>この割り当ては一つの最適解にすぎない</b> ——
            同じ χ を与える配役は複数あり、どの役が誰に付くかは一意でない。
          </p>
        </div>
      </div>

      {over && (
        <>
          <h2>三人に収まらない役</h2>
          <p className="lede">
            グラフから取り除けば三彩色になる<b>最小</b>の役集合を厳密に求めた。
            最小解が複数あるときは、そのどれを外しても等しく解消する。
          </p>
          <div className="note note--warn">
            <strong>最小 {ex.excess} 役</strong>
            {ex.is_clique && (
              <>
                。候補 {ex.union.length} 役は<b>クリークを成す</b>(互いに全員が同席する)ので、
                <b>特定の一役を「四人目」と呼ぶことはできない</b>。
              </>
            )}
            <br />
            <span className="grc">{ex.union.join(" ・ ")}</span>
            <br />
            {ex.host_scenes.length > 0 ? (
              <>この {ex.union.length} 役が同席する場面: 第 {ex.host_scenes.join("、第 ")} 場面</>
            ) : (
              <>単一の場面には揃わず、複数の場面にまたがる組として現れる</>
            )}
          </div>
          {ex.candidates_total > ex.candidates.length && (
            <p style={{ fontSize: ".8rem", color: "var(--ink-faint)" }}>
              最小解は全部で {ex.candidates_total} 通りあり、ここには最初の {ex.candidates.length} 通りだけを載せている。
            </p>
          )}
          <div className="tablewrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>取り除けば三人で足りる役</th>
                </tr>
              </thead>
              <tbody>
                {ex.candidates.map((c, k) => (
                  <tr key={k}>
                    <td className="num">{k + 1}</td>
                    <td className="grc">{c.join(" + ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      <h2>対照</h2>
      <p className="lede">
        役のラベルだけを篇内で無作為に置換した偽の劇(seed {ctlLoose.seed}・{ctlLoose.trials.toLocaleString()} 回)と比べる。
        置換は発話数・場面の数と大きさ・境界・役の数をすべて保ち、
        <b>どの役がどの場面に集まるか</b>だけを壊す。
      </p>
      <div className="tablewrap">
        <table>
          <thead>
            <tr>
              <th>境界</th>
              <th className="num">実測 χ</th>
              <th className="num">偽の劇の平均</th>
              <th className="num">範囲</th>
              <th className="num">p</th>
            </tr>
          </thead>
          <tbody>
            {(["loose", "strict"] as const).map((m) => {
              const c = d.control[m];
              return (
                <tr key={m}>
                  <td>{m === "loose" ? "緩" : "厳"}</td>
                  <td className="num">{c.observed}</td>
                  <td className="num">{c.null_mean.toFixed(2)}</td>
                  <td className="num">
                    {c.null_min}–{c.null_max}
                  </td>
                  <td className="num" style={{ color: c.p < 0.01 ? undefined : "var(--tone-4)" }}>
                    {c.p < 0.001 ? c.p.toExponential(1) : c.p.toFixed(3)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {ctlLoose.observed > ctlLoose.null_mean && (
        <div className="note note--warn">
          <strong>この篇では実測が偽の劇の平均を上回っている。</strong>
          偶然より「悪く」見えるということで、方法の弱点の徴候である。
          合唱隊が語らない区間(とくに合唱隊登場前のプロロゴス)では退場を検出できず、
          実際には同席していない役が結ばれる。<Link href="/method/" prefetch={false}>方法</Link>を参照。
        </div>
      )}

      {d.review_labels.length > 0 && (
        <>
          <h2>決着しない話者ラベル</h2>
          <p className="lede">
            この篇には、本文からは役の同定が決まらないラベルがある。
            古典文献学の未決問題であって実装の不備ではないので、
            <b>両方の読みで χ を出している</b>。
          </p>
          <dl className="kv">
            <dt>ラベル</dt>
            <dd className="grc">{d.review_labels.join(" ・ ")}</dd>
            <dt>読み A</dt>
            <dd>
              χ = {d.chi.A_loose}(緩)/ {d.chi.A_strict}(厳)
            </dd>
            <dt>読み B</dt>
            <dd>
              χ = {d.chi.B_loose}(緩)/ {d.chi.B_strict}(厳)
            </dd>
          </dl>
          {d.chi.A_loose === d.chi.B_loose && d.chi.A_strict === d.chi.B_strict && (
            <p className="note">
              <strong>この論争は結論に影響しない。</strong>どちらの読みでも χ は変わらなかった。
            </p>
          )}
        </>
      )}

      <h2>底本と権利</h2>
      <dl className="kv">
        <dt>CTS URN</dt>
        <dd style={{ fontSize: ".82rem", wordBreak: "break-all" }}>{d.urn}</dd>
        <dt>校訂者</dt>
        <dd>{d.edition.editor || "—"}</dd>
        <dt>底本</dt>
        <dd>
          {d.edition.title || "—"}
          {d.edition.date ? `(${d.edition.date})` : ""}
          {d.edition.ref && (
            <>
              {" "}
              <a href={d.edition.ref}>原本</a>
            </>
          )}
        </dd>
        <dt>提供</dt>
        <dd>
          <a href="https://github.com/PerseusDL/canonical-greekLit">
            Perseus Digital Library, Tufts University
          </a>
        </dd>
        <dt>ライセンス</dt>
        <dd>
          <a href="https://creativecommons.org/licenses/by-sa/4.0/deed.ja">CC BY-SA 4.0</a>
        </dd>
      </dl>

      <nav style={{ display: "flex", justifyContent: "space-between", marginTop: "2.5rem", fontSize: ".88rem" }}>
        <span>
          {prev && (
            <Link href={`/play/${prev.id}/`} prefetch={false}>
              ← {prev.ja}
            </Link>
          )}
        </span>
        <span>
          {next && (
            <Link href={`/play/${next.id}/`} prefetch={false}>
              {next.ja} →
            </Link>
          )}
        </span>
      </nav>
    </main>
  );
}
