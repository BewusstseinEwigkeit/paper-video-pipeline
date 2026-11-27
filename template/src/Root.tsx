import { Composition } from "remotion";
import { Full, Part } from "./film/Full";
import { FPS, H, W } from "./film/theme";
import { FULL_FRAMES } from "./film/vo";
import { KIT_DEMO_FRAMES, KitDemo } from "./kit/KitDemo";
import { Sampler } from "./kit/Sampler";

// 1280x720 design canvas; deliver 1080p with --scale=1.5
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Full" component={Full} durationInFrames={FULL_FRAMES} fps={FPS} width={W} height={H} />
    <Composition id="Clip" component={Part} defaultProps={{ from: 0 }} durationInFrames={FULL_FRAMES} fps={FPS} width={W} height={H} />
    <Composition id="Sampler" component={Sampler} defaultProps={{ start: 0.5, step: 3 }} durationInFrames={Math.max(1, Math.floor(FULL_FRAMES / FPS / 3))} fps={FPS} width={W} height={H} />
    <Composition id="KitDemo" component={KitDemo} durationInFrames={KIT_DEMO_FRAMES} fps={FPS} width={W} height={H} />
  </>
);
