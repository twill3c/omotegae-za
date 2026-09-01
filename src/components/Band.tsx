import { CLAIMED_ACTORS } from "@/lib/site";

export interface BandItem {
  kind: "scene" | "chorus";
  roles?: string[];
  sp: number;
}

/** 同席役数に応じた色。三人までと、それを超えるものを分ける。 */
function tone(n: number): string {
  if (n <= 2) return "var(--tone-2)";
  if (n === CLAIMED_ACTORS) return "var(--tone-3)";
  if (n === CLAIMED_ACTORS + 1) return "var(--tone-4)";
  return "var(--tone-many)";
}

/**
 * 骨格帯 —— 発話の進行に沿って、場面と合唱歌(境界)を並べる。
 *
 * 幅は発話数に比例。場面は同席役数で色を塗り、合唱歌は灰色にする。
 * **境界を描かないと合唱歌の位置が見えない** —— 劇の骨格は
 * 場面と合唱歌の交替そのものなので、片方だけでは骨格にならない。
 */
export function Band({ items, height }: { items: BandItem[]; height?: number }) {
  let sceneIndex = -1;
  return (
    <div className="band" style={height ? { height: `${height}px` } : undefined}>
      {items.map((s, i) => {
        if (s.kind === "chorus") {
          return (
            <div
              key={i}
              className="band__seg band__seg--chorus"
              style={{ flex: `${s.sp} 0 0` }}
              title={`合唱歌 — 発話 ${s.sp}(ここで登退場が起こりうる)`}
            />
          );
        }
        sceneIndex += 1;
        const roles = s.roles ?? [];
        return (
          <div
            key={i}
            className="band__seg"
            style={{ flex: `${s.sp} 0 0`, background: tone(roles.length) }}
            title={
              `第 ${sceneIndex} 場面 — 発話 ${s.sp} / 役 ${roles.length}` +
              (roles.length ? `\n${roles.join(" ・ ")}` : "")
            }
          />
        );
      })}
    </div>
  );
}
