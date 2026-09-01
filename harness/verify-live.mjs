// **本番**を実リクエストと実ブラウザで検品する。
//
//   node harness/verify-live.mjs [https://...]
//
// ローカルの out/ 検査は配信の前までしか見られない。
// 判定は `vercel ls` ではなく**本番 URL への実リクエスト**で行う
// ([[vercel-deploy-quirks]])。

import { chromium } from "playwright";

const ORIGIN = (process.argv[2] ?? "https://omotegae-za.vercel.app").replace(/\/$/, "");

const problems = [];
const fail = (where, msg) => problems.push(`${where}: ${msg}`);

const PAGES = [
  "/",
  "/method/",
  "/play/tlg0085.tlg006/",
  "/play/tlg0085.tlg006/read/",
  "/play/tlg0019.tlg009/",
  "/play/tlg0019.tlg009/read/",
  "/play/tlg0011.tlg004/",
];

console.log(`検品先: ${ORIGIN}`);

// ---- HTTP 直の検査 --------------------------------------------------------
for (const path of PAGES) {
  const res = await fetch(ORIGIN + path);
  if (res.status !== 200) {
    fail(path, `HTTP ${res.status}`);
    continue;
  }
  const ct = res.headers.get("content-type") ?? "";
  if (!/text\/html/.test(ct)) fail(path, `Content-Type が ${ct}`);
  const html = await res.text();
  // G-00: 権利表示が本番でも欠けていないこと
  if (path.startsWith("/play/") && !path.endsWith("read/")) {
    if (!html.includes("Perseus Digital Library")) fail(path, "Perseus 帰属が無い");
    if (!html.includes("CC BY-SA 4.0")) fail(path, "ライセンス表示が無い");
  }
  // N-03: 日本語本文にキリル文字が混ざっていないこと
  const cyr = html.match(/[Ѐ-ӿ]/g);
  if (cyr) fail(path, `キリル文字 ${cyr.length} 件`);
}

// ---- 実ブラウザ -----------------------------------------------------------
const browser = await chromium.launch();
for (const theme of ["light", "dark"]) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, colorScheme: theme });
  for (const path of PAGES) {
    const page = await ctx.newPage();
    const errs = [];
    page.on("console", (m) => m.type() === "error" && errs.push(m.text()));
    page.on("pageerror", (e) => errs.push(String(e)));
    page.on("response", (r) => r.status() >= 400 && errs.push(`HTTP ${r.status()} ${r.url()}`));
    await page.goto(ORIGIN + path, { waitUntil: "networkidle" });
    if (errs.length) fail(`${path}[${theme}]`, `${errs.length} 件: ${errs[0]}`);
    const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    if (over > 1) fail(`${path}[${theme}]`, `横に ${over}px はみ出している`);
    await page.close();
  }
  await ctx.close();
}

// ---- 内部リンクがすべて生きているか(出荷後の 404 は目で見ても分からない)----
const seen = new Set();
const res = await fetch(ORIGIN + "/");
const home = await res.text();
for (const m of home.matchAll(/href="(\/[^"#]*)"/g)) seen.add(m[1]);
console.log(`トップから辿れる内部リンク ${seen.size} 件を確認する`);
for (const href of seen) {
  const r = await fetch(ORIGIN + href, { method: "HEAD" });
  if (r.status !== 200) fail(href, `HTTP ${r.status}`);
}

await browser.close();

if (problems.length) {
  console.error(`問題 ${problems.length} 件:`);
  for (const p of problems) console.error("  " + p);
  process.exit(1);
}
console.log("問題 0 件 — 本番検品を通過");
