// HUD tag: frosted dark chip with a coloured status dot, lifted above a point on a thin leader line.
// x, y = the point it labels (e.g. a trajectory tip projected to the screen); o = opacity; check / cross fade in a verdict.
import React from "react";
import { SANS, UI } from "../film/theme";

export const Tag: React.FC<{ x: number; y: number; color: string; text: string; sub?: string; o: number; check?: number; cross?: number }> = ({ x, y, color, text, sub, o, check = 0, cross = 0 }) =>
  o <= 0.01 ? null : (
    <div style={{ position: "absolute", left: x, top: y, opacity: o }}>
      <div style={{ position: "absolute", left: -0.5, top: -26, width: 1, height: 26, background: `linear-gradient(${color}00, ${color})` }} />
      <div style={{ position: "absolute", left: -3, top: -3, width: 6, height: 6, borderRadius: 3, background: color, boxShadow: `0 0 8px ${color}` }} />
      <div style={{ position: "absolute", left: 0, top: -26, transform: "translate(-50%, -100%)", display: "flex", alignItems: "center", gap: 7, padding: "3px 9px 3px 7px", borderRadius: 7, background: "rgba(10,14,23,0.82)", border: `1px solid ${color}80`, backdropFilter: "blur(6px)", whiteSpace: "nowrap" }}>
        <div style={{ width: 6, height: 6, borderRadius: 3, background: color }} />
        <div style={{ fontFamily: SANS, fontWeight: 700, fontStretch: "88%", fontSize: 17, letterSpacing: 0.4, color: "#E8EEF6", fontFeatureSettings: '"tnum" 1' }}>{text}</div>
        {sub && <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 13, color, opacity: 0.95 }}>{sub}</div>}
        {check > 0 && <div style={{ opacity: check, fontFamily: SANS, fontWeight: 700, fontSize: 15, color: "#34D399" }}>✓</div>}
        {cross > 0 && <div style={{ opacity: cross, fontFamily: SANS, fontWeight: 700, fontSize: 15, color: UI.mute }}>✕</div>}
      </div>
    </div>
  );
