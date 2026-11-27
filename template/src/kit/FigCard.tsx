// Paper figure card with timed zoom and spotlight.
// The camera eases between focus rectangles (fractions 0..1 of the image); everything outside the highlight is dimmed
// and the highlight gets a cyan outline. Use it to walk through the framework figure module by module:
//   <FigCard src="figs/fig2.png" iw={4400} ih={2133} t={t} tIn={at("m1") - 0.4} tOut={at("m4", undefined, true) + 0.6}
//     x={120} y={90} w={1040} focus={[{ t: at("m2"), r: [0.62, 0.01, 0.38, 0.47] }, { t: at("m3"), r: [0.62, 0.51, 0.38, 0.49] }]} />
// Put the original high-resolution figure in public/ (chat apps shrink images to about 2000 px).
import React from "react";
import { Img, staticFile } from "remotion";
import { UI, clamp01, easeIO, lerp, ramp } from "../film/theme";

export type Rect = [number, number, number, number];
type View = { x: number; y: number; w: number; h: number };

export type FigCardProps = {
  src: string;          // file in public/ (or a URL)
  zoomSrc?: string;     // optional sharper crop source that fades in when zoomed past ~1.2x
  iw: number;           // image pixel size
  ih: number;
  t: number;
  tIn: number;          // card fades in at tIn, out at tOut
  tOut: number;
  x: number;            // card box on the 1280x720 canvas
  y: number;
  w: number;
  h?: number;
  maxH?: number;
  bg?: string;          // figure background (white for most papers)
  leadDelay?: number;   // seconds the whole figure stays before the first focus move
  focus?: Array<{ t: number; r: Rect; hl?: Rect }>; // r = camera view, hl = explicit highlight (defaults to r)
  dim?: number;         // matte strength for explicit highlights
  bare?: boolean;       // no card chrome (inside an existing panel)
};

export const FigCard: React.FC<FigCardProps> = ({
  src, zoomSrc, iw, ih, t, tIn, tOut, x, y, w, h: hProp, maxH = 440, bg = "#FFFFFF", leadDelay = 3.0, focus = [], dim = 0.5, bare = false,
}) => {
  const h = hProp ?? Math.min(maxH, w * 0.6);
  const vw = w - (bare ? 0 : 28);
  const vh = h - (bare ? 0 : 28);
  if (t < tIn || t > tOut || tOut <= tIn || iw <= 0 || ih <= 0 || vw <= 0 || vh <= 0) return null;

  // fit a rectangle into the viewport, centred, letterboxing beyond the image edges when needed
  const fit = (r: Rect): View => {
    const rx = r[0] * iw, ry = r[1] * ih, rw = Math.max(1, r[2] * iw), rh = Math.max(1, r[3] * ih);
    const units = Math.max(rw / vw, rh / vh);
    const width = vw * units, height = vh * units;
    return { x: rx + rw / 2 - width / 2, y: ry + rh / 2 - height / 2, w: width, h: height };
  };

  const steps = [...focus].sort((a, b) => a.t - b.t);
  const firstFocus = tIn + leadDelay;
  let previousStart = firstFocus - 0.8;
  let previous = fit([0, 0, 1, 1]);
  let view = previous;
  for (const step of steps) {
    const start = Math.max(step.t, firstFocus, previousStart + 0.8);
    if (t < start) break;
    const target = fit(step.r);
    const p = easeIO(ramp(t, start, start + 0.8));
    view = { x: lerp(previous.x, target.x, p), y: lerp(previous.y, target.y, p), w: lerp(previous.w, target.w, p), h: lerp(previous.h, target.h, p) };
    if (t < start + 0.8) break;
    previous = target;
    previousStart = start;
  }

  const scale = vw / view.w;
  let hl: Rect | null = null, hlK = 0, prevHl: Rect | null = null, explicit = false;
  for (const st of steps) {
    const start = Math.max(st.t, firstFocus);
    if (t < start) break;
    const target = st.hl ?? (st.r[2] >= 0.99 && st.r[3] >= 0.99 ? null : st.r);
    prevHl = hl; hl = target; explicit = !!st.hl; hlK = easeIO(ramp(t, start, start + 0.6));
  }
  const toScreen = (r: Rect) => ({ x: (r[0] * iw - view.x) * scale, y: (r[1] * ih - view.y) * scale, w: r[2] * iw * scale, h: r[3] * ih * scale });
  const hb = hl ? toScreen(hl) : null;
  const pb = prevHl ? toScreen(prevHl) : null;
  const box = hb && pb ? { x: lerp(pb.x, hb.x, hlK), y: lerp(pb.y, hb.y, hlK), w: lerp(pb.w, hb.w, hlK), h: lerp(pb.h, hb.h, hlK) } : hb;
  const matteO = hb ? (pb ? 1 : hlK) : 0;
  const zoomO = zoomSrc ? clamp01((0.88 - view.w / iw) / 0.22) : 0;
  const opacity = bare ? 1 : Math.min(ramp(t, tIn, tIn + 0.5), 1 - ramp(t, tOut - 0.4, tOut));
  const resolveSrc = (s: string) => (/^(?:https?:|data:|blob:)/.test(s) ? s : staticFile(s));
  const roundedHole = (b: { x: number; y: number; w: number; h: number }, r = 8) => {
    const rr = Math.min(r, b.w / 2, b.h / 2);
    return `M0,0H${vw}V${vh}H0Z M${b.x + rr},${b.y}h${b.w - 2 * rr}a${rr},${rr},0,0,1,${rr},${rr}v${b.h - 2 * rr}a${rr},${rr},0,0,1,${-rr},${rr}h${-(b.w - 2 * rr)}a${rr},${rr},0,0,1,${-rr},${-rr}v${-(b.h - 2 * rr)}a${rr},${rr},0,0,1,${rr},${-rr}Z`;
  };
  const imgStyle: React.CSSProperties = { position: "absolute", display: "block", maxWidth: "none", left: -view.x * scale, top: -view.y * scale, width: iw * scale, height: ih * scale };

  return (
    <div style={{
      position: "absolute", left: x, top: y, width: w, height: h, boxSizing: "border-box", padding: bare ? 0 : 12,
      background: bare ? "transparent" : "rgba(14,20,34,0.92)", border: bare ? "none" : "2px solid rgba(148,163,184,0.22)",
      borderRadius: bare ? 10 : 16, boxShadow: bare ? "none" : UI.shadow, overflow: "hidden", opacity,
    }}>
      <div style={{ position: "relative", width: vw, height: vh, overflow: "hidden", borderRadius: bare ? 10 : 8, background: bg }}>
        <Img src={resolveSrc(src)} alt="Paper figure" draggable={false} style={imgStyle} />
        {zoomSrc && zoomO > 0.01 && <Img src={resolveSrc(zoomSrc)} alt="Paper figure detail" draggable={false} style={{ ...imgStyle, opacity: zoomO }} />}
        {box && matteO > 0 && (
          <svg width={vw} height={vh} style={{ position: "absolute", inset: 0, opacity: matteO }}>
            <path fillRule="evenodd" fill={explicit ? `rgba(15,23,42,${dim})` : "#0F172A"} d={roundedHole(box, 8)} />
            <rect x={box.x} y={box.y} width={box.w} height={box.h} rx={8} fill="none" stroke="#22D3EE" strokeWidth={explicit ? 2.5 : 1.5} strokeOpacity={explicit ? 1 : 0.65} />
          </svg>
        )}
      </div>
    </div>
  );
};
