// Bar chart pieces for SVG results panels: an axis with ticks and bars that grow on their own narration cue.
// Render inside <svg width={1280} height={720}>. A bar shows a dashed placeholder from preAt (so rows do not shift when
// later bars appear), grows at cue, and shows its value at valueAt (useful when a BigNumber flies into that slot).
import React from "react";
import { DUR, ease } from "../film/motion";
import { MONO, SANS, UI, easeOut, ramp } from "../film/theme";

const NUM: React.CSSProperties = { fontFamily: MONO, fontFeatureSettings: '"tnum" 1' };

export const Axis: React.FC<{ x: number; y: number; width: number; min: number; max: number; ticks: number[]; top: number; o?: number }> = ({ x, y, width, min, max, ticks, top, o = 1 }) => (
  <g opacity={o}>
    <line x1={x} x2={x + width} y1={y} y2={y} stroke={UI.hair} />
    {ticks.map((v) => {
      const px = x + ((v - min) / (max - min)) * width;
      return (
        <g key={v}>
          <line x1={px} x2={px} y1={top} y2={y + 7} stroke={UI.hair} opacity={0.6} />
          <text x={px} y={y + 34} textAnchor="middle" fill={UI.mute} fontSize={22} style={NUM}>{v}</text>
        </g>
      );
    })}
  </g>
);

export type BarProps = {
  t: number; cue: number; label: string; value: number; color: string; y: number;
  x?: number; width?: number; min?: number; max?: number; labelX?: number; valueAt?: number; preAt?: number; digits?: number;
};

export const Bar: React.FC<BarProps> = ({ t, cue, label, value, color, y, x = 280, width = 760, min = 0, max = 100, labelX = 80, valueAt, preAt, digits = 1 }) => {
  const length = ((value - min) / (max - min)) * width;
  const show = ramp(t, cue, cue + 0.2);
  const grow = easeOut(ramp(t, cue, cue + 0.6));
  const pre = preAt === undefined ? 0 : 0.45 * ease(t, preAt, DUR.base);
  return (
    <>
      {pre > 0 && (
        <g opacity={pre * (1 - show)}>
          <text x={labelX} y={y + 8} fontSize={22} fill={UI.mute} style={{ fontFamily: SANS, fontWeight: 600 }}>{label}</text>
          <rect x={x} y={y - 18} width={length} height={36} rx={4} fill="none" stroke={UI.hair} strokeDasharray="4 6" />
        </g>
      )}
      <g opacity={show}>
        <text x={labelX} y={y + 8} fontSize={22} fill={UI.text} style={{ fontFamily: SANS, fontWeight: 600 }}>{label}</text>
        <rect x={x} y={y - 18} width={length * grow} height={36} rx={4} fill={color} />
        <text x={x + length + 14} y={y + 9} fontSize={26} fill={UI.text} style={NUM} opacity={valueAt === undefined ? 1 : ramp(t, valueAt, valueAt + 0.15)}>{value.toFixed(digits)}</text>
      </g>
    </>
  );
};
