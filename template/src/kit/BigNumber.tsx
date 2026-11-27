// Headline number: rises digit by digit in the middle of the frame, then shrinks and flies into a bar's value slot
// (dock), so the number and the bar read as the same object. Pair with <Bar valueAt={tDock + 0.8}>.
// from = optional origin point (e.g. the method's dot on a number line): the number grows out of it.
import React from "react";
import { EASE, RevealNumber, RevealText, ease } from "../film/motion";
import { C, SANS, UI, clamp01, lerp, ramp } from "../film/theme";

export const BigNumber: React.FC<{
  t: number; tIn: number; tDock: number; value: string; unit?: string; sub?: string; dock: [number, number]; from?: [number, number]; color?: string; dockSize?: number;
}> = ({ t, tIn, tDock, value, unit = "", sub = "", dock, from, color = C.A, dockSize = 26 }) => {
  const tEnd = tDock + 0.95;
  if (t < tIn - 0.05 || t > tEnd) return null;
  const SIZE = 168;
  const d = EASE.inOut(clamp01((t - tDock) / 0.8));
  const o = 1 - ramp(t, tDock + 0.8, tEnd);
  const g = from ? EASE.out(clamp01((t - tIn) / 0.75)) : 1;
  const ds = EASE.out(clamp01((t - tDock) / 0.8)); // shrink early so the flight never covers the growing bar
  const sc = lerp(1, dockSize / SIZE, ds) * lerp(0.12, 1, g);
  const CY = from ? 222 : 292;
  const dy = EASE.out(clamp01((t - tDock) / 0.55)); // drop first, slide later: a curved path below the other rows
  const x = lerp(lerp(from ? from[0] : 640, 640, g), dock[0], d);
  const y = lerp(lerp(from ? from[1] : CY, CY, g), dock[1], dy);
  return (
    <div style={{ position: "absolute", left: x, top: y, transform: "translate(-50%, -50%)", opacity: o, textAlign: "center", whiteSpace: "nowrap" }}>
      <div style={{ transform: `scale(${sc})`, transformOrigin: "50% 50%" }}>
        <RevealNumber value={value} t={t} t0={tIn} style={{ fontFamily: SANS, fontWeight: 600, fontStretch: "112%", fontSize: SIZE, lineHeight: 1, color, letterSpacing: -4, fontFeatureSettings: '"tnum" 1' }} />
      </div>
      <div style={{ position: "absolute", left: "50%", top: "100%", transform: "translateX(-50%)", marginTop: 14, opacity: 1 - ease(t, tDock, 0.35), textAlign: "center" }}>
        {unit && <RevealText text={unit} t={t} t0={tIn + 0.35} style={{ fontFamily: SANS, fontWeight: 500, fontSize: 28, fontStretch: "105%", color: UI.text, letterSpacing: 0.3 }} />}
        {sub && <div style={{ marginTop: 6 }}><RevealText text={sub} t={t} t0={tIn + 0.5} style={{ fontFamily: SANS, fontWeight: 450, fontSize: 26, color: UI.mute }} /></div>}
      </div>
    </div>
  );
};
