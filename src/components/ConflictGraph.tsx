/**
 * 配役盤 —— 衝突グラフと彩色。
 *
 * 頂点 = 語る役、辺 = 同じ場面に居合わせる二役(同一俳優が兼ねられない)。
 * 頂点の色は割り当てられた俳優。**同色の頂点は辺で結ばれていない** ——
 * それが「その配役で上演できる」ということである。
 */

const ACTOR_COLORS = [
  "#4a6f96",
  "#8c3b2e",
  "#6f8f6a",
  "#b5762e",
  "#7a5c8f",
  "#3f8c8c",
  "#a3554f",
  "#5c6f3f",
  "#8f6f3f",
  "#4f5f8f",
  "#8f4f6f",
  "#6f6f6f",
];

export function ConflictGraph({
  vertices,
  edges,
  cast,
  size = 420,
}: {
  vertices: string[];
  edges: string[][];
  cast: Record<string, string[]>;
  size?: number;
}) {
  const colorOf = new Map<string, number>();
  for (const [c, roles] of Object.entries(cast)) {
    for (const r of roles) colorOf.set(r, Number(c));
  }
  const n = vertices.length;
  const R = size / 2 - 74;
  const cx = size / 2;
  const cy = size / 2;
  const pos = new Map<string, [number, number]>();
  vertices.forEach((v, i) => {
    const a = (2 * Math.PI * i) / n - Math.PI / 2;
    pos.set(v, [cx + R * Math.cos(a), cy + R * Math.sin(a)]);
  });

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width="100%"
      style={{ maxWidth: `${size}px`, display: "block" }}
      role="img"
      aria-label={`衝突グラフ: ${n} 役 / ${edges.length} 辺 / ${Object.keys(cast).length} 俳優`}
    >
      <g stroke="var(--rule)" strokeWidth="1">
        {edges.map(([a, b], i) => {
          const p = pos.get(a);
          const q = pos.get(b);
          if (!p || !q) return null;
          return <line key={i} x1={p[0]} y1={p[1]} x2={q[0]} y2={q[1]} />;
        })}
      </g>
      {vertices.map((v) => {
        const [x, y] = pos.get(v)!;
        const c = colorOf.get(v) ?? 0;
        const right = x >= cx - 1;
        return (
          <g key={v}>
            <circle cx={x} cy={y} r={6} fill={ACTOR_COLORS[c % ACTOR_COLORS.length]}>
              <title>{`${v} — 俳優 ${c + 1}`}</title>
            </circle>
            <text
              x={x + (right ? 10 : -10)}
              y={y + 3.5}
              textAnchor={right ? "start" : "end"}
              fontSize="10"
              fill="var(--ink-soft)"
              fontFamily="var(--grc)"
            >
              {v.length > 16 ? v.slice(0, 15) + "…" : v}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export { ACTOR_COLORS };
