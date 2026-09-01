import type { NextConfig } from "next";

// 静的書き出しのみ。サーバ関数も cron も持たない(SPEC N-01)。
// 解析結果はすべてビルド時に確定しているので、実行時に外へ出る経路が要らない。
const nextConfig: NextConfig = {
  output: "export",
  reactStrictMode: true,
  trailingSlash: true,
  images: { unoptimized: true },
};

export default nextConfig;
