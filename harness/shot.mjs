// 出荷 HTML を**実ブラウザ**で開いて撮る(G-10)。
//
//   node harness/shot.mjs              # ローカルの out/ を撮る
//   node harness/shot.mjs https://...  # 本番を撮る
//
// hanshichi-atlas の教訓: **図のはみ出しは代理指標では捕まらない。**
// 撮って目で見る工程を省かない。あわせて、機械で見える範囲
// (横スクロール・コンソール誤り・要素の欠落)はここで数える。

import { createServer } from "node:http";
import { readFile, mkdir, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { chromium } from "playwright";

const ROOT = path.resolve(import.meta.dirname, "..");
const OUT = path.join(ROOT, "out");
const SHOTS = path.join(ROOT, "out-shots");

const PAGES = [
  ["index", "/"],
  ["method", "/method/"],
  ["play-choephori", "/play/tlg0085.tlg006/"],
  ["play-persians", "/play/tlg0085.tlg002/"],
  ["play-birds", "/play/tlg0019.tlg006/"],
  ["read-choephori", "/play/tlg0085.tlg006/read/"],
  ["read-frogs", "/play/tlg0019.tlg009/read/"],
];

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon",
  ".woff2": "font/woff2",
};

async function serveOut() {
  const server = createServer(async (req, res) => {
    const url = decodeURIComponent((req.url ?? "/").split("?")[0]);
    let file = path.join(OUT, url);
    if (url.endsWith("/")) file = path.join(file, "index.html");
    if (!existsSync(file)) file += ".html";
    try {
      const body = await readFile(file);
      res.writeHead(200, { "Content-Type": MIME[path.extname(file)] ?? "application/octet-stream" });
      res.end(body);
    } catch {
      res.writeHead(404, { "Content-Type": "text/plain" });
      res.end("not found");
    }
  });
  await new Promise((r) => server.listen(0, r));
  return { server, origin: `http://127.0.0.1:${server.address().port}` };
}

const problems = [];
const fail = (where, msg) => problems.push(`${where}: ${msg}`);

const arg = process.argv[2];
let origin = arg;
let server = null;
if (!arg) {
  const s = await serveOut();
  server = s.server;
  origin = s.origin;
}
console.log(`検品先: ${origin}`);

await mkdir(SHOTS, { recursive: true });
const browser = await chromium.launch();

for (const theme of ["light", "dark"]) {
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 1,
    colorScheme: theme,
  });
  for (const [name, route] of PAGES) {
    const page = await ctx.newPage();
    const errors = [];
    page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
    page.on("pageerror", (e) => errors.push(String(e)));
    page.on("requestfailed", (r) => errors.push(`要求失敗 ${r.url()}`));
    page.on("response", (r) => r.status() >= 400 && errors.push(`HTTP ${r.status()} ${r.url()}`));
    const resp = await page.goto(origin + route, { waitUntil: "networkidle" });
    if (!resp || resp.status() !== 200) fail(route, `HTTP ${resp?.status()}`);
    if (errors.length) fail(route, `コンソール誤り ${errors.length} 件: ${errors[0]}`);

    // 横はみ出し —— 本文が横スクロールしていないか
    const over = await page.evaluate(() => {
      const d = document.documentElement;
      return d.scrollWidth - d.clientWidth;
    });
    if (over > 1) fail(`${route}[${theme}]`, `横に ${over}px はみ出している`);

    // 骨格帯が実際に描かれているか(空の帯を出していないか)
    if (route === "/") {
      const segs = await page.locator(".band__seg").count();
      if (segs < 500) fail(route, `骨格帯の区画が ${segs} しかない`);
      const rows = await page.locator(".bandrow").count();
      if (rows !== 45) fail(route, `帯の行が ${rows}(45 でない)`);
    }
    if (route.includes("/play/") && !route.endsWith("read/")) {
      const nodes = await page.locator("svg circle").count();
      if (nodes < 3) fail(route, `衝突グラフの頂点が ${nodes} しかない`);
    }

    // 文字色と背景が同じになっていないか(テーマ切替の事故)
    const contrast = await page.evaluate(() => {
      const s = getComputedStyle(document.body);
      return [s.color, s.backgroundColor];
    });
    if (contrast[0] === contrast[1]) fail(`${route}[${theme}]`, `文字色と背景色が同じ ${contrast[0]}`);

    await page.screenshot({
      path: path.join(SHOTS, `${name}-${theme}.png`),
      fullPage: route !== "/play/tlg0085.tlg006/read/" && !route.endsWith("read/"),
    });
    await page.close();
  }
  await ctx.close();
}

// 携帯幅でのはみ出し
const mob = await browser.newContext({ viewport: { width: 390, height: 844 }, colorScheme: "light" });
for (const [name, route] of PAGES) {
  const page = await mob.newPage();
  await page.goto(origin + route, { waitUntil: "networkidle" });
  const over = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  if (over > 1) fail(`${route}[390px]`, `横に ${over}px はみ出している`);
  await page.screenshot({ path: path.join(SHOTS, `${name}-mobile.png`), fullPage: false });
  await page.close();
}
await mob.close();

await browser.close();
server?.close();

await writeFile(path.join(SHOTS, "report.txt"), problems.join("\n") + "\n", "utf-8");
if (problems.length) {
  console.error(`問題 ${problems.length} 件:`);
  for (const p of problems) console.error("  " + p);
  process.exit(1);
}
console.log(`問題 0 件 — 画像は out-shots/ に ${PAGES.length * 3} 枚`);
