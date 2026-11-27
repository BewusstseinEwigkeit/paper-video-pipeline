// The whole film on one timeline. Scenes decide their own visibility from narration times (at()).
import React from "react";
import { AbsoluteFill, Audio, staticFile, useCurrentFrame } from "remotion";
import { CFG } from "./config";
import { FilmTexture } from "./motion";
import { Scenes } from "./Scenes";
import { Caption, SectionTag } from "./Shell";
import { ChapterLeak } from "../kit/ChapterLeak";
import { FPS, UI } from "./theme";

export const Scene: React.FC<{ t: number }> = ({ t }) => (
  <AbsoluteFill style={{ background: `radial-gradient(ellipse at 50% 40%, #101827 0%, ${UI.bg} 70%)` }}>
    <Scenes t={t} />
    {CFG.chapterLeak && <ChapterLeak t={t} />}
    <FilmTexture frame={Math.round(t * FPS)} grain={0.04} vignette={0.48} />
    <SectionTag t={t} />
    <Caption t={t} />
  </AbsoluteFill>
);

export const Full: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Scene t={f / FPS} />
      {CFG.audio && <Audio src={staticFile(CFG.audio)} />}
    </AbsoluteFill>
  );
};

// Section preview with audio offset: render [from, from + frames) of the film, e.g. --props='{"from":26}' --frames=0-449
export const Part: React.FC<{ from: number }> = ({ from }) => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill>
      <Scene t={from + f / FPS} />
      {CFG.audio && <Audio src={staticFile(CFG.audio)} startFrom={Math.round(from * FPS)} />}
    </AbsoluteFill>
  );
};
