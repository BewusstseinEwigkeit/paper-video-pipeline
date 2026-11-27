// Motion language for the film: named easings, durations, and text/number/bar primitives.
// Everything is a pure function of time t (seconds) so it renders identically frame by frame.
import React from "react";
import { Easing } from "remotion";
import { clamp01 } from "./theme";

// ---- easings (cubic-bezier, same values as CSS) ----
export const EASE = {
  out: Easing.bezier(0.16, 1, 0.3, 1), // default entrance: fast start, long soft landing
  inOut: Easing.bezier(0.65, 0, 0.35, 1), // camera and shared-element moves
  in: Easing.bezier(0.7, 0, 0.84, 0), // exits
  snap: Easing.bezier(0.2, 0.9, 0.1, 1), // UI chips, small labels
};
export const DUR = { micro: 0.22, short: 0.45, base: 0.7, long: 1.1 }; // seconds
export const STAGGER = { char: 0.025, word: 0.055, item: 0.12 };

export const ease = (t: number, t0: number, dur: number, e: (x: number) => number = EASE.out) => e(clamp01((t - t0) / dur));

// ---- text: per-word mask rise + blur-to-sharp, optional exit ----
export const RevealText: React.FC<{
  text: string; t: number; t0: number; t1?: number; style?: React.CSSProperties; stagger?: number; dur?: number;
  rise?: number; blur?: number; wordStyle?: (w: string, i: number) => React.CSSProperties | undefined;
}> = ({ text, t, t0, t1, style, stagger = STAGGER.word, dur = DUR.base, rise = 0.55, blur = 8, wordStyle }) => {
  // Latin text reveals word by word; Chinese (no spaces) character by character
  const cjk = !/\s/.test(text.trim()) && /[\u3400-\u9fff]/.test(text);
  const words = cjk ? Array.from(text) : text.split(" ");
  const exit = t1 === undefined ? 0 : ease(t, t1, DUR.short, EASE.in);
  if (t < t0 - 0.01 || exit >= 1) return null;
  return (
    <span style={{ display: "inline-block", ...style }}>
      {words.map((w, i) => {
        const k = ease(t, t0 + i * stagger, dur);
        const ko = 1 - exit;
        return (
          <span key={i} style={{ display: "inline-block", overflow: "hidden", verticalAlign: "bottom", paddingBottom: "0.08em", marginRight: !cjk && i < words.length - 1 ? "0.25em" : 0 }}>
            <span style={{
              display: "inline-block", transform: `translateY(${(1 - k) * rise * 100}%)`, opacity: k * ko,
              filter: blur > 0 && k < 1 ? `blur(${(1 - k) * blur}px)` : undefined, ...(wordStyle?.(w, i) || {}),
            }}>{w}</span>
          </span>
        );
      })}
    </span>
  );
};

// ---- numbers: each character rises in on its own beat (no rolling counters) ----
export const RevealNumber: React.FC<{ value: string; t: number; t0: number; style?: React.CSSProperties }> = ({ value, t, t0, style }) => (
  <span style={{ display: "inline-flex", ...style }}>
    {value.split("").map((ch, i) => {
      const k = ease(t, t0 + i * 0.06, DUR.long);
      return (
        <span key={i} style={{ display: "inline-block", overflow: "hidden", padding: "0.06em 0" }}>
          <span style={{ display: "inline-block", transform: `translateY(${(1 - k) * 105}%)`, filter: k < 1 ? `blur(${(1 - k) * 10}px)` : undefined }}>{ch}</span>
        </span>
      );
    })}
  </span>
);

// ---- a soft light sweep across a just-finished bar or card ----
export const Sweep: React.FC<{ t: number; t0: number; w: number; h: number; r?: number }> = ({ t, t0, w, h, r = 4 }) => {
  const k = clamp01((t - t0) / 0.9);
  if (k <= 0 || k >= 1) return null;
  const x = -0.4 * w + k * 1.8 * w;
  return (
    <div style={{ position: "absolute", inset: 0, borderRadius: r, overflow: "hidden", pointerEvents: "none" }}>
      <div style={{ position: "absolute", top: 0, left: x, width: w * 0.35, height: h, background: "linear-gradient(90deg, transparent, rgba(255,255,255,0.45), transparent)", transform: "skewX(-20deg)" }} />
    </div>
  );
};

// ---- film texture: subtle animated grain + vignette over everything ----
const grainCache = new Map<number, string>();
const grainURL = (seed: number) => {
  const k = seed % 8;
  if (grainCache.has(k)) return grainCache.get(k)!;
  if (typeof document === "undefined") return "";
  const cv = document.createElement("canvas"); cv.width = cv.height = 256;
  const g = cv.getContext("2d")!; const img = g.createImageData(256, 256);
  let s = 1234 + k * 977;
  for (let i = 0; i < img.data.length; i += 4) { s = (s * 16807) % 2147483647; const v = (s / 2147483647) * 255; img.data[i] = img.data[i + 1] = img.data[i + 2] = v; img.data[i + 3] = 255; }
  g.putImageData(img, 0, 0);
  const url = cv.toDataURL(); grainCache.set(k, url); return url;
};
export const FilmTexture: React.FC<{ frame: number; grain?: number; vignette?: number }> = ({ frame, grain = 0.05, vignette = 0.55 }) => (
  <>
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none", backgroundImage: `url(${grainURL(Math.floor(frame / 2))})`, backgroundSize: "256px 256px", opacity: grain, mixBlendMode: "overlay" }} />
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none", background: `radial-gradient(ellipse at 50% 45%, transparent 55%, rgba(0,0,0,${vignette}) 100%)` }} />
  </>
);
