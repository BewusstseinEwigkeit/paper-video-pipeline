// Soft light leak at chapter boundaries (@remotion/effects lightLeak, screen blend). Chapters come from CFG.sections;
// keep the opacity low (0.12-0.2): around 0.5 the whole frame turns cyan.
import React from "react";
import { Solid } from "remotion";
import { lightLeak } from "@remotion/effects/light-leak";
import { CFG } from "../film/config";
import { H, W, clamp01 } from "../film/theme";
import { at } from "../film/vo";

export const ChapterLeak: React.FC<{ t: number; opacity?: number; dur?: number; hueShift?: number }> = ({ t, opacity = 0.12, dur = 1.1, hueShift = 200 }) => {
  const cuts = CFG.sections.map(([id], i) => [id, 3 + i * 8] as const);
  const hit = cuts.find(([id]) => t > at(id) - 0.75 && t < at(id) - 0.75 + dur);
  if (!hit) return null;
  const p = clamp01((t - (at(hit[0]) - 0.75)) / dur);
  return (
    <div style={{ position: "absolute", inset: 0, mixBlendMode: "screen", opacity, pointerEvents: "none" }}>
      <Solid width={W} height={H} color="#000000" effects={[lightLeak({ seed: hit[1], hueShift, progress: p })]} />
    </div>
  );
};
