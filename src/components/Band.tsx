import { CLAIMED_ACTORS } from "@/lib/site";

export interface Scene {
  roles: string[];
  sp: number;
}

/** 同席役数に応じた色。三人までと、それを超えるものを分ける。 */
function tone(n: number): string {
  if (n <= 2) return "var(--tone-2)";
  if (n === CLAIMED_ACTORS) return "var(--tone-3)";
  if (n === CLAIMED_ACTORS + 1) return "var(--tone-4)";
  return "var(--tone-many)";
}

export function Band({ scenes, height }: { scenes: Scene[]; height?: number }) {
  const total = scenes.reduce((s, x) => s + x.sp, 0) || 1;
  return (
    <div className="band" style={height ? { height: `${height}px` } : undefined}>
      {scenes.map((s, i) => (
        <div
          key={i}
          className={"band__seg" + (s.roles.length === 0 ? " band__seg--chorus" : "")}
          style={{
            flex: `${s.sp} 0 0`,
            background: s.roles.length === 0 ? undefined : tone(s.roles.length),
          }}
          title={
            `第 ${i} 場面 — 発話 ${s.sp} / 役 ${s.roles.length}` +
            (s.roles.length ? `\n${s.roles.join(" ・ ")}` : "(合唱隊のみ)")
          }
        />
      ))}
      {/* 幅は発話数に比例する。合計 ${total} 発話。 */}
    </div>
  );
}
