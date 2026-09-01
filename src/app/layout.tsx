import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "面替え座 — ギリシア四大劇作家 45 篇を上演の骨格として読む",
  description:
    "アイスキュロス・ソポクレス・エウリピデス・アリストパネスの現存全 45 篇について、" +
    "何人の俳優で上演できるかを厳密に計算し、三人に収まらない役を特定する。",
};

const FOOTER = {
  license: "https://github.com/twill3c/omotegae-za/blob/main/LICENSE",
  dataLicense: "https://creativecommons.org/licenses/by-sa/4.0/deed.ja",
  repository: "https://github.com/twill3c/omotegae-za",
  perseus: "https://github.com/PerseusDL/canonical-greekLit",
  appMenu: "https://app-menu-amber.vercel.app/",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ja">
      <body>
        <header className="masthead">
          <div className="masthead__inner">
            <Link href="/" className="masthead__title">
              面替え座
            </Link>
            <span className="masthead__sub">ギリシア四大劇作家 45 篇</span>
            <nav>
              <Link href="/">骨格帯</Link>
              <Link href="/method/">方法</Link>
            </nav>
          </div>
        </header>
        {children}
        <footer className="site-footer">
          <div className="site-footer__inner">
            <a href={FOOTER.license}>コード: MIT</a>
            <span className="fsep">・</span>
            <a href={FOOTER.dataLicense}>データと訳文: CC BY-SA 4.0</a>
            <span className="fsep">・</span>
            <a href={FOOTER.perseus}>原典: Perseus Digital Library, Tufts University</a>
            <span className="fsep">・</span>
            <a href={FOOTER.repository}>GitHub</a>
            <span className="fsep">・</span>
            <a href={FOOTER.appMenu}>App Menu</a>
            <span className="site-footer__copy">© 2026 坂田哲朗</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
