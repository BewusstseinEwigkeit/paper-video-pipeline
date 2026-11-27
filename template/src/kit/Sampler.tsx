// Review helper: frame i shows the film at time start + i * step (no audio). Render it once and tile the frames into a
// contact sheet for a design review; much faster than one `remotion still` per frame:
//   npx remotion render Sampler out/sampler.mp4 --props='{"start":0.5,"step":3}' --frames=0-79
import React from "react";
import { useCurrentFrame } from "remotion";
import { Scene } from "../film/Full";

export const Sampler: React.FC<{ start: number; step: number }> = ({ start, step }) => {
  const f = useCurrentFrame();
  return <Scene t={start + f * step} />;
};
