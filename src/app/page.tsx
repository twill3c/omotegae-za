import Link from "next/link";
import { AUTHORS, CLAIMED_ACTORS, PLAYS, playsOf, type PlaySummary } from "@/lib/site";
import { Band } from "@/components/Band";
import { loadPlay } from "@/lib/load";

export default function Home() {
  const details = Object.fromEntries(PLAYS.map((p) => [p.id, loadPlay(p.id)]));
  const tragedies = PLAYS.filter((p) => p.genre === "悲劇");
  const comedies = PLAYS.filter((p) => p.genre === "喜劇");
  const fits = (ps: PlaySummary[], mode: string) =>
    ps.filter((p) => p.chi[mode] <= CLAIMED_ACTORS).length;

  return (
    <main className="wrap" style={{ paddingTop: "2rem" }}>
      <h1>面替え座</h1>
      <p className="lede">
        古典期アテナイの上演では、語る俳優は最大三人だったとされる。俳優は面を替えて複数の役を兼ねた。
        この規約が現存する台本そのものから復元できるかを、四大劇作家の全 45 篇で測った。
        役を頂点、同じ場面に居合わせることを辺とするグラフの<b>彩色数 χ</b> が、
        その篇の上演に要る俳優の数である。
      </p>

      <div className="note">
        <strong>χ ≤ 3 の篇:</strong> 悲劇 {fits(tragedies, "A_loose")}/{tragedies.length}(緩)・
        {fits(tragedies, "A_strict")}/{tragedies.length}(厳)、
        喜劇 {fits(comedies, "A_loose")}/{comedies.length}(緩)。
        <br />
        当初は「悲劇 34 篇のうち 31 篇以上で χ ≤ 3」を事前登録したが、
        <b>この予測は落ちた</b>。落ちた経緯と、それでも出た構造は
        <Link href="/method/" prefetch={false}>方法</Link>に記した。
      </div>

      <h2>骨格帯</h2>
      <p className="lede">
        横軸は発話の進行(幅は発話数に比例)。場面は<b>そこに居合わせる役の数</b>で塗り、
        合唱歌は灰色にした。灰色の位置で登退場が起こりうる。
        <Legend />
      </p>

      {AUTHORS.map((author) => (
        <section key={author}>
          <h3>
            {author}{" "}
            <span style={{ color: "var(--ink-faint)", fontWeight: 400, fontSize: ".85rem" }}>
              {playsOf(author).length} 篇
            </span>
          </h3>
          {playsOf(author).map((p) => (
            <div className="bandrow" key={p.id}>
              <Link href={`/play/${p.id}/`} prefetch={false} className="bandrow__name">
                {p.ja}
              </Link>
              <Band items={details[p.id].band.A_loose} />
              <span
                className="bandrow__chi"
                style={{ color: p.chi.A_loose > CLAIMED_ACTORS ? "var(--tone-many)" : "var(--ink-soft)" }}
                title={`χ = ${p.chi.A_loose}(緩)/ ${p.chi.A_strict}(厳)`}
              >
                {p.chi.A_loose}
              </span>
            </div>
          ))}
        </section>
      ))}

      <h2>一覧</h2>
      <div className="tablewrap">
        <table>
          <thead>
            <tr>
              <th>篇</th>
              <th>原題</th>
              <th>作家</th>
              <th className="num">行</th>
              <th className="num">発話</th>
              <th className="num">役</th>
              <th className="num">χ 緩</th>
              <th className="num">χ 厳</th>
              <th className="num">場面 緩</th>
            </tr>
          </thead>
          <tbody>
            {PLAYS.map((p) => (
              <tr key={p.id}>
                <td>
                  <Link href={`/play/${p.id}/`} prefetch={false}>
                    {p.ja}
                  </Link>
                </td>
                <td className="grc">{p.grc}</td>
                <td>{p.author}</td>
                <td className="num">{p.lines.toLocaleString()}</td>
                <td className="num">{p.sp.toLocaleString()}</td>
                <td className="num">{p.vertices}</td>
                <td
                  className="num"
                  style={{ color: p.chi.A_loose > CLAIMED_ACTORS ? "var(--tone-many)" : undefined }}
                >
                  {p.chi.A_loose}
                </td>
                <td className="num">{p.chi.A_strict}</td>
                <td className="num">{p.scenes.loose}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="note note--warn">
        <strong>作家間の比較について。</strong>
        Perseus の校訂本文は<b>作家ごとに校訂者が一人</b>である(アイスキュロス=Smyth、
        ソポクレス=Storr、エウリピデス=Murray、アリストパネス=Hall &amp; Geldart)。
        マークアップ由来の量は校訂者間の差と分離できない。
        上の表で校訂実務に左右されにくいのは<b>話者の系列</b>と<b>合唱隊の発話位置</b>で、
        χ はそこから導いている。行数・発話数は書式の影響を受ける。
      </div>
    </main>
  );
}

function Legend() {
  const items: [string, string][] = [
    ["1–2 役", "var(--tone-2)"],
    ["3 役", "var(--tone-3)"],
    ["4 役", "var(--tone-4)"],
    ["5 役以上", "var(--tone-many)"],
    ["合唱歌(境界)", "var(--chorus)"],
  ];
  return (
    <span style={{ display: "inline-flex", flexWrap: "wrap", gap: ".8rem", marginLeft: ".6rem" }}>
      {items.map(([label, color]) => (
        <span key={label} style={{ display: "inline-flex", alignItems: "center", gap: ".3rem" }}>
          <span
            style={{ width: "12px", height: "12px", background: color, borderRadius: "2px", display: "inline-block" }}
          />
          <span style={{ fontSize: ".8rem" }}>{label}</span>
        </span>
      ))}
    </span>
  );
}
