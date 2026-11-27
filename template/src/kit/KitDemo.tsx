// Kit showcase on its own 12-second clock (no narration needed): npx remotion studio -> KitDemo.
// In a real film replace the fixed seconds below with at() anchors.
import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { FilmTexture } from "../film/motion";
import { C, FPS, UI, fade } from "../film/theme";
import { Axis, Bar } from "./Chart";
import { BigNumber } from "./BigNumber";
import { FigCard } from "./FigCard";
import { Tag } from "./Tag";

export const KIT_DEMO_FRAMES = 12 * FPS;
const FIG = { src: "kit/demo-figure.svg", w: 1600, h: 800 };
const MIN = 40, MAX = 50, X0 = 300, WIDTH = 700;
const valueX = (v: number) => X0 + ((v - MIN) / (MAX - MIN)) * WIDTH + 14 + 30;

export const KitDemo: React.FC = () => {
  const t = useCurrentFrame() / FPS;
  const chartO = fade(t, 6.0, 6.4, 11.4, 11.9);
  return (
    <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, #101827 0%, ${UI.bg} 70%)` }}>
      <FigCard src={FIG.src} iw={FIG.w} ih={FIG.h} t={t} tIn={0.2} tOut={6.0} x={140} y={110} w={1000} h={500} leadDelay={1.2}
        focus={[{ t: 2.4, r: [0.27, 0.15, 0.24, 0.68] }, { t: 4.0, r: [0.53, 0.27, 0.22, 0.45] }]} />
      <Tag x={835} y={590} color={C.A} text="Module B" sub="new" o={fade(t, 2.9, 3.2, 3.9, 4.1)} check={fade(t, 3.3, 3.5, 9, 10)} />
      <div style={{ position: "absolute", inset: 0, opacity: chartO }}>
        <svg width={1280} height={720} style={{ position: "absolute", inset: 0 }}>
          <Axis x={X0} y={620} width={WIDTH} min={MIN} max={MAX} ticks={[40, 42, 44, 46, 48, 50]} top={440} />
          <Bar t={t} cue={7.0} label="Baseline" value={45.1} color="#55647D" y={560} x={X0} width={WIDTH} min={MIN} max={MAX} labelX={110} preAt={6.2} />
          <Bar t={t} cue={8.6} label="XYZ" value={48.2} color={C.A} y={490} x={X0} width={WIDTH} min={MIN} max={MAX} labelX={110} preAt={6.2} valueAt={9.4} />
        </svg>
      </div>
      <BigNumber t={t} tIn={6.6} tDock={8.6} value="48.2" sub="on the benchmark" dock={[valueX(48.2), 490]} />
      <FilmTexture frame={Math.round(t * FPS)} grain={0.04} vignette={0.48} />
    </AbsoluteFill>
  );
};
