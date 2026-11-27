// Example scenes. Each one decides its own visibility from narration anchors - never from absolute seconds:
//   at("b2", "classify")     -> when the word "classify" is spoken in line b2
//   at("p1")                 -> start of line p1;   at("p1", undefined, true) -> its end
// Replace these with the film's own beats; keep the pattern (fade windows built from at(), words revealed on cue).
// The same scenes run on narration.example.json (English) and narration.zh.example.json (Chinese): cards read their text
// from the narration, and the anchors are Latin terms and numbers that both scripts say.
import React from "react";
import { EASE, RevealNumber, RevealText } from "./motion";
import { ACCENT, C, SANS, UI, clamp01, fade, lerp } from "./theme";
import { VO, at } from "./vo";
import { FigCard } from "../kit/FigCard";

const SERIF_IT: React.CSSProperties = { fontFamily: "'Instrument Serif', serif", fontStyle: "italic", fontWeight: 400 };
const verbatim = (id: string) => VO[id].text.replace(/[.。]$/, "");
const TITLE_ACCENT = ["details", "细节"]; // title word(s) set in coral serif italic

// title / closing card (the line is shown verbatim, so it is listed in CFG.silentLines)
const TitleCard: React.FC<{ t: number; id: string }> = ({ t, id }) => {
  const t0 = at(id), t1 = at(id, undefined, true);
  const o = fade(t, t0 - 0.6, t0, t1 + 0.8, t1 + 1.4);
  if (o <= 0) return null;
  const accent = (w: string) => TITLE_ACCENT.some((a) => a === w.toLowerCase() || (/[\u3400-\u9fff]/.test(w) && a.includes(w)));
  return (
    <div style={{ position: "absolute", left: 80, right: 80, top: 290, textAlign: "center", opacity: o }}>
      <RevealText text={verbatim(id)} t={t} t0={t0 - 0.4} stagger={0.09} dur={1.0}
        style={{ fontFamily: SANS, fontWeight: 600, fontSize: 64, fontStretch: "108%", letterSpacing: -1.8, color: UI.text }}
        wordStyle={(w) => (accent(w) ? { ...SERIF_IT, fontSize: 78, color: "#F87171", letterSpacing: 0 } : undefined)} />
    </div>
  );
};

// b1: an abstract image with region proposals appearing across the line (timed by the line's start / end only,
// so the same scene works for any narration language)
const BOXES: Array<[number, number, number, number, boolean]> = [
  [70, 60, 150, 110, false], [260, 40, 120, 160, true], [420, 90, 170, 120, false], [120, 210, 130, 100, false],
  [300, 230, 110, 80, true], [470, 240, 140, 90, false], [40, 330, 120, 60, false], [560, 40, 70, 70, false],
];
const Regions: React.FC<{ t: number }> = ({ t }) => {
  const t0 = at("b1"), t1 = at("b1", undefined, true);
  const o = fade(t, t0 - 0.3, t0 + 0.3, t1 + 0.2, t1 + 0.7);
  if (o <= 0) return null;
  return (
    <div style={{ position: "absolute", left: 320, top: 150, width: 640, height: 400, opacity: o, borderRadius: 14, overflow: "hidden",
      background: "linear-gradient(135deg, #1B2638 0%, #0F1726 60%, #172235 100%)", border: "1px solid rgba(148,163,184,0.2)" }}>
      {BOXES.map(([x, y, w, h, hot], i) => {
        const k = EASE.out(clamp01((t - lerp(t0 + 0.2, t1 - 0.8, i / (BOXES.length - 1))) / 0.45));
        const col = hot ? "#F87171" : ACCENT;
        return <div key={i} style={{ position: "absolute", left: x, top: y, width: w, height: h, borderRadius: 4,
          border: `1.5px solid ${col}`, opacity: k, transform: `scale(${lerp(1.08, 1, k)})`, background: hot ? "rgba(248,113,113,0.08)" : "transparent" }} />;
      })}
    </div>
  );
};

// b2: typographic step line (numerals + serif italic words + hairlines that fill with the narration; no boxes, no glow)
const Pipeline: React.FC<{ t: number }> = ({ t }) => {
  const o = fade(t, at("b2") - 0.2, at("b2") + 0.4, at("b2", undefined, true) + 0.2, at("b2", undefined, true) + 0.7);
  if (o <= 0) return null;
  const steps: Array<[string, string, number]> = [["01", "Propose", at("b2", "propose")], ["02", "Classify", at("b2", "classify")], ["03", "Refine", at("b2", "refine")]];
  return (
    <div style={{ position: "absolute", left: 0, right: 0, top: 280, display: "flex", justifyContent: "center", alignItems: "flex-end", gap: 26, opacity: o, fontFamily: SANS }}>
      {steps.map(([num, name, ts], i) => {
        const k = EASE.out(clamp01((t - ts + 0.1) / 0.5));
        const fill = EASE.inOut(clamp01((t - ts + 0.35) / 0.45));
        return (
          <React.Fragment key={name}>
            {i > 0 && (
              <div style={{ position: "relative", width: 70, height: 1, marginBottom: 22, background: "rgba(241,245,249,0.22)" }}>
                <div style={{ position: "absolute", left: 0, top: 0, height: 1, width: `${fill * 100}%`, background: "rgba(241,245,249,0.85)" }} />
              </div>
            )}
            <div style={{ opacity: lerp(0.3, 1, k), transform: `translateY(${(1 - k) * 8}px)` }}>
              <div style={{ fontWeight: 600, fontSize: 13, letterSpacing: 1.6, color: k > 0.5 ? (i === 2 ? "#F87171" : ACCENT) : UI.mute }}>{num}</div>
              <div style={{ ...SERIF_IT, fontSize: 56, lineHeight: 1, color: i === 2 && k > 0.5 ? "#F87171" : "#F1F5F9" }}>{name}</div>
            </div>
          </React.Fragment>
        );
      })}
    </div>
  );
};

// p1: a question card (verbatim, caption silenced)
const Question: React.FC<{ t: number }> = ({ t }) => {
  const t0 = at("p1"), t1 = at("p1", undefined, true);
  const o = fade(t, t0 - 0.25, t0 + 0.2, t1 + 0.4, t1 + 0.9);
  if (o <= 0) return null;
  return (
    <div style={{ position: "absolute", left: 80, right: 80, top: 300, textAlign: "center", opacity: o }}>
      <RevealText text={VO.p1.text} t={t} t0={t0 - 0.1} stagger={0.07} dur={0.8}
        style={{ fontFamily: SANS, fontWeight: 600, fontSize: 46, letterSpacing: -1.1, color: UI.text }} />
    </div>
  );
};

// r1: a headline number that lands when it is spoken, plus a baseline bar that grows on its own word
const Headline: React.FC<{ t: number }> = ({ t }) => {
  const t0 = at("r1"), t1 = at("r1", undefined, true);
  const o = fade(t, t0 - 0.3, t0 + 0.2, t1 + 0.6, t1 + 1.1);
  if (o <= 0) return null;
  const tOurs = at("r1", "48.2"), tBase = at("r1", "45.1");
  const bar = (v: number, ts: number, col: string, label: string, y: number) => {
    const k = EASE.out(clamp01((t - ts) / 0.6));
    return (
      <div style={{ position: "absolute", left: 340, top: y, display: "flex", alignItems: "center", gap: 18, opacity: k }}>
        <div style={{ width: 110, fontFamily: SANS, fontWeight: 600, fontSize: 20, color: UI.mute, textAlign: "right" }}>{label}</div>
        <div style={{ width: 520 * ((v - 40) / 10) * k, height: 26, borderRadius: 4, background: col }} />
        <div style={{ fontFamily: SANS, fontWeight: 600, fontSize: 22, color: UI.text, fontFeatureSettings: '"tnum" 1' }}>{v.toFixed(1)}</div>
      </div>
    );
  };
  return (
    <div style={{ position: "absolute", inset: 0, opacity: o }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 150, textAlign: "center" }}>
        <RevealNumber value="48.2" t={t} t0={tOurs - 0.1} style={{ fontFamily: SANS, fontWeight: 600, fontSize: 150, fontStretch: "112%", letterSpacing: -4, color: C.A, fontFeatureSettings: '"tnum" 1' }} />
      </div>
      {bar(48.2, tOurs + 0.4, C.A, "XYZ", 420)}
      {bar(45.1, tBase, "#55647D", "Baseline", 466)}
    </div>
  );
};

// m1-m2: the framework figure (placeholder in public/kit/) walked through module by module with FigCard
const Method: React.FC<{ t: number }> = ({ t }) => (
  <FigCard src="kit/demo-figure.svg" iw={1600} ih={800} t={t} tIn={at("m1") - 0.4} tOut={at("m2", undefined, true) + 0.8}
    x={190} y={100} w={900} h={450} leadDelay={1.0}
    focus={[{ t: at("m1", undefined, true) - 0.6, r: [0.27, 0.15, 0.24, 0.68] }, { t: at("m2") + 0.2, r: [0.53, 0.27, 0.22, 0.45] }]} />
);

export const Scenes: React.FC<{ t: number }> = ({ t }) => (
  <>
    <Regions t={t} />
    <Method t={t} />
    <TitleCard t={t} id="c0a" />
    <Pipeline t={t} />
    <Question t={t} />
    <Headline t={t} />
    <TitleCard t={t} id="e1" />
  </>
);
