// Captions (serif with coloured italic keywords) and dark-glass chapter progress marks.
import React from "react";
import { ACCENT, BENTO, CAPTION, LOOK, SANS, UI, fade, ramp } from "./theme";
import { at, captionAt, sep } from "./vo";
import { CFG } from "./config";

const RULES: Array<[RegExp, React.CSSProperties]> = [
  ...CFG.captionKeywords.map(([words, color]): [RegExp, React.CSSProperties] => [new RegExp(`^(${words.join("|")})$`, "i"), { color, fontStyle: "italic" }]),
  [new RegExp(`^(${CFG.methodWords.join("|")})$`), { color: ACCENT, fontStyle: "italic", fontWeight: 600 }],
  [/^\d+(\.\d+)?$/, { fontWeight: 700, fontFeatureSettings: '"tnum" 1' }],
];

const styled = (word: string) => {
  const m = word.match(/^([^A-Za-z0-9]*)([A-Za-z0-9.'-]*?)([^A-Za-z0-9]*)$/);
  const core = m ? m[2] : word;
  const rule = RULES.find(([re]) => re.test(core.replace(/-$/, "")));
  if (!rule || !m) return word;
  return (
    <>
      {m[1]}
      <span style={rule[1]}>{core}</span>
      {m[3]}
    </>
  );
};

const SILENT = new Set(CFG.silentLines); // lines shown verbatim on a card get no caption

export const Caption: React.FC<{ t: number }> = ({ t }) => {
  const s = captionAt(t);
  if (!s || SILENT.has(s.id)) return null;
  const seamlessIn = s.start - s.prevEnd < 0.35;
  const seamlessOut = s.nextStart - s.end < 0.35;
  const inO = seamlessIn ? 1 : ramp(t, s.start - 0.02, s.start + 0.1);
  const outO = seamlessOut ? 1 : 1 - ramp(t, s.end + 0.12, s.end + 0.25);
  const o = Math.min(inO, outO);
  const dark = LOOK === "night";

  return (
    <>
      {dark && (
        <div
          style={{
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            height: 146,
            background: "linear-gradient(180deg, rgba(6,10,18,0) 0%, rgba(6,10,18,0.72) 58%, rgba(6,10,18,0.92) 100%)",
            opacity: o,
            pointerEvents: "none",
          }}
        />
      )}
      <div style={{ position: "absolute", left: 0, right: 0, bottom: 26, display: "flex", justifyContent: "center", opacity: o }}>
        <div
          style={{
            maxWidth: 1060,
            padding: "7px 20px",
            borderRadius: 10,
            background: dark ? "rgba(8,13,24,0.82)" : "rgba(251,250,247,0.86)",
            border: dark ? "1px solid rgba(148,163,184,0.16)" : "none",
            backdropFilter: "blur(8px)",
            color: UI.text,
            fontFamily: CAPTION,
            fontWeight: 460,
            fontSize: 27,
            lineHeight: 1.3,
            textAlign: "center",
            textShadow: dark ? "0 1px 8px rgba(0,0,0,0.65)" : "none",
          }}
        >
          {s.words.map(([w, w0], i) => {
            const lit = 0.88 + 0.12 * Math.min(1, Math.max(0, (t - w0 + 0.05) / 0.18));
            return (
              <React.Fragment key={i}>
                {i > 0 && sep(s.words[i - 1][0], w)}
                <span style={{ opacity: lit }}>{styled(w)}</span>
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </>
  );
};

const SECTIONS = CFG.sections;

export const SectionTag: React.FC<{ t: number }> = ({ t }) => {
  let cur = -1;
  SECTIONS.forEach(([id], i) => {
    if (t >= at(id) - 0.3) cur = i;
  });
  if (cur < 0 || !SECTIONS[cur][1]) return null;
  const o = fade(t, at("b1") - 0.3, at("b1") + 0.3, at("e1") - 0.5, at("e1"));

  return (
    <div
      style={{
        position: "absolute",
        left: 36,
        top: 20,
        opacity: o,
        display: "inline-flex",
        alignItems: "center",
        gap: 12,
        padding: "5px 14px 5px 8px",
        borderRadius: 999,
        background: BENTO.bg,
        border: `1px solid ${BENTO.border}`,
        boxShadow: "0 8px 24px rgba(0,0,0,0.38)",
      }}
    >
      {SECTIONS.filter(([, name]) => name).map(([id, name], i) => {
        const on = i === cur;
        const k = on ? fade(t, at(id) - 0.3, at(id) + 0.2, 1e9, 1e9 + 1) : 0;
        return (
          <div key={id} style={{ display: "flex", alignItems: "center", gap: 7 }}>
            <div
              style={{
                width: 20,
                height: 20,
                borderRadius: 10,
                border: `1.5px solid ${on ? ACCENT : UI.mute}`,
                background: on ? ACCENT : "transparent",
                color: on ? "#060A12" : UI.mute,
                fontFamily: SANS,
                fontSize: 12,
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                opacity: on ? 1 : 0.6,
                boxShadow: on ? `0 0 10px ${ACCENT}66` : "none",
              }}
            >
              {i + 1}
            </div>
            {on && (
              <div
                style={{
                  fontFamily: SANS,
                  fontWeight: 700,
                  fontSize: 13,
                  letterSpacing: 1.5,
                  textTransform: "uppercase",
                  color: UI.text,
                  opacity: k,
                }}
              >
                {name}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
};
