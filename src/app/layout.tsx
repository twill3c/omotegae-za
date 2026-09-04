import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "面替え座 — ギリシア四大劇作家 45 篇を上演の骨格として読む",
  description:
    "アイスキュロス・ソポクレス・エウリピデス・アリストパネスの現存全 45 篇について、" +
    "何人の俳優で上演できるかを厳密に計算し、三人に収まらない役を特定する。",
};

/**
 * フリート共通のフッタ(koho-lens が正本)。
 * 5 項目・この並び・下部固定。区切りの「・」は文字として置く
 * (CSS の ::before で描くと innerText に出ず、検品器から見えない)。
 *
 * このサイトは訳文が CC BY-SA 4.0 で継承があり、原典の帰属表示が G-00 の要求なので、
 * 5 項目の下にもう一行だけ付ける(senoto-mori など架空題材四作と同じ形)。
 */
const FOOTER = {
  license: "https://github.com/twill3c/omotegae-za/blob/main/LICENSE",
  dataLicense: "https://creativecommons.org/licenses/by-sa/4.0/deed.ja",
  repository: "https://github.com/twill3c/omotegae-za",
  perseus: "https://github.com/PerseusDL/canonical-greekLit",
  appMenu: "https://app-menu-amber.vercel.app/",
  arukikata: "https://claude.ai/code/artifact/dc91a605-dc0b-4baf-aaaf-6728f49ad1a4",
  sekkeizu: "https://claude.ai/code/artifact/8cf8228f-e469-401f-8b7e-bc6bcfaf359f",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <header className="masthead">
          <div className="masthead__inner">
            <Link href="/" prefetch={false} className="masthead__title">
              面替え座
            </Link>
            <span className="masthead__sub">ギリシア四大劇作家 45 篇</span>
            <nav>
              <Link href="/" prefetch={false}>骨格帯</Link>
              <Link href="/method/" prefetch={false}>方法</Link>
            </nav>
          </div>
        </header>
        {children}
        {/* fleet: fixed footer */}
        <nav className="fleet" aria-label="フリート共通リンク">
          <p className="fleet__row">
            <a href={FOOTER.license} target="_blank" rel="noopener">MIT License</a>
            <span className="fleet__copy"> © 2026 坂田哲朗</span>
            <span className="fsep">・</span>
            <a href={FOOTER.repository} target="_blank" rel="noopener">GitHub</a>
            <span className="fsep">・</span>
            <a href={FOOTER.arukikata} target="_blank" rel="noopener">面替え座の歩き方</a>
            <span className="fsep">・</span>
            <a href={FOOTER.sekkeizu} target="_blank" rel="noopener">面替え座 設計図</a>
            <span className="fsep">・</span>
            <a href={FOOTER.appMenu} target="_blank" rel="noopener">App Menu</a>
          </p>
          <p className="fleet__note">
            原典 <a href={FOOTER.perseus} target="_blank" rel="noopener">Perseus Digital Library, Tufts University</a>
            {" "}—— データと訳文は{" "}
            <a href={FOOTER.dataLicense} target="_blank" rel="noopener">CC BY-SA 4.0</a>
          </p>
        </nav>
      </body>
    </html>
  );
}
