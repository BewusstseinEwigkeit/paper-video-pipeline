// Design tokens (docs/02). Change colours here only; every scene reads from C / UI.
import { continueRender, delayRender, staticFile } from "remotion";

export const FPS = 30;
// Whole-film look switch: "ink" (paper + ink mountains, porcelain viaduct), "studio" (daylight asphalt), "night" (dark slate).
export type Look = "ink" | "studio" | "night";
export const LOOK = "night" as Look; // plain tech look
export const PAPER = "#F4F2ED";
export const W = 1280;
export const H = 720;

export const C = {
  bg: "#EEF1F5", // studio daylight ground
  bg2: "#E3E8EF",
  card: "#FBFCFD",
  ink: "#0E1A2B",
  ink2: "#3B4A5F",
  mute: "#7A8799",
  hair: "#CBD3DE",
  asphalt: "#5C6470",
  line: "#F4F6F9",
  // one colour = one object for the whole film (e.g. main object A red, comparison objects B1-B3 blue / green / purple)
  A: "#E5484D",
  B1: "#3E7BFA",
  B2: "#1FA971",
  B3: "#8E5BE8",
  pool: "#9AA5B4", // the other native proposals
  gain: "#F2A33A", // improvement / refined highlight
  ours: "#0E1A2B",
};
export const B_COLORS = [C.B1, C.B2, C.B3];

// Mona Sans (GitHub, OFL): variable width 75-125 + weight 200-900 + tabular figures; one family for titles, UI and numbers
// Chinese glyphs fall back to the CJK faces after the Latin ones (Latin keeps Mona Sans / Source Serif 4)
export const SANS = "'Mona Sans', 'Inter', 'Segoe UI', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif";
// One text family (Inter, tabular numerals for data) plus one display face for titles only.
export const SERIF = LOOK === "ink" ? "'Playfair Display', Georgia, 'Noto Serif SC', 'Songti SC', serif" : "'Mona Sans', 'Inter', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif";
export const TITLE_STYLE: "italic" | "normal" = LOOK === "ink" ? "italic" : "normal";
export const MONO = "'Mona Sans', 'Inter', 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif";
// serif caption face with coloured italic keywords
export const CAPTION = "'Source Serif 4', Georgia, 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', serif";
export const ACCENT = "#5FD3E8"; // method / module names

const FONTS: Array<[string, string, string, string, string?]> = [
  ["Mona Sans", "fonts/MonaSans.ttf", "normal", "200 900", "75% 125%"],
  ["Instrument Serif", "fonts/InstrumentSerif-Italic.ttf", "italic", "400"],
  ["Instrument Serif", "fonts/InstrumentSerif-Regular.ttf", "normal", "400"],
  ["Source Serif 4", "fonts/SourceSerif4.ttf", "normal", "200 900"],
  ["Source Serif 4", "fonts/SourceSerif4-Italic.ttf", "italic", "200 900"],
];
if (typeof document !== "undefined") {
  const h = delayRender("film fonts");
  Promise.all(FONTS.map(([fam, src, style, weight, stretch]) => new FontFace(fam, `url(${staticFile(src)})`, { style, weight, ...(stretch ? { stretch } : {}) }).load().then((f) => { document.fonts.add(f); })))
    .then(() => continueRender(h)).catch(() => continueRender(h));
}

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const ramp = (t: number, a: number, b: number) => clamp01((t - a) / (b - a));
export const easeIO = (x: number) => { const c = clamp01(x); return c < 0.5 ? 4 * c * c * c : 1 - Math.pow(-2 * c + 2, 3) / 2; };
export const easeOut = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);
export const expoOut = (x: number) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * clamp01(x)));
export const lerp = (a: number, b: number, k: number) => a + (b - a) * k;
export const fade = (t: number, a: number, b: number, c: number, d: number) => Math.min(ramp(t, a, b), 1 - ramp(t, c, d));
export const smooth = (k: number) => { const c = clamp01(k); return c * c * (3 - 2 * c); };

// Flat UI colours that follow LOOK (2D overlays, charts, captions).
export const PANEL = LOOK === "night" ? "rgba(14,20,34,0.88)" : "#FBFAF7";
export const BENTO = {
  bg: "rgba(14,20,34,0.88)",
  bgDeep: "rgba(8,13,24,0.94)",
  border: "rgba(148,163,184,0.18)",
  borderActive: "rgba(95,211,232,0.52)",
  borderCoral: "rgba(229,72,77,0.55)",
  glowCyan: "linear-gradient(90deg, rgba(95,211,232,0) 0%, rgba(95,211,232,0.85) 50%, rgba(95,211,232,0) 100%)",
  glowCoral: "linear-gradient(90deg, rgba(229,72,77,0) 0%, rgba(229,72,77,0.9) 50%, rgba(229,72,77,0) 100%)",
  shadow: "0 22px 60px rgba(0,0,0,0.58), inset 0 1px 0 rgba(255,255,255,0.06)",
};
export const UI = LOOK === "night"
  ? { bg: "#060A12", card: "#F8FAFC", text: "#F8FAFC", mute: "#B8C4D4", dim: "#7D8CA3", hair: "rgba(148,163,184,0.22)", base: "#55647D", shadow: "0 22px 60px rgba(0,0,0,0.62)" }
  : LOOK === "ink"
    ? { bg: PAPER, card: "#FBFAF7", text: "#16294A", mute: "#7C8798", dim: "#7C8798", hair: "#D9D4CA", base: "#A9B3C2", shadow: "0 22px 50px rgba(22,41,74,0.12)" }
    : { bg: "#EEF1F5", card: "#FBFCFD", text: "#0E1A2B", mute: "#7A8799", dim: "#7A8799", hair: "#CBD3DE", base: "#A7B0BC", shadow: "0 22px 50px rgba(14,26,43,0.12)" };
