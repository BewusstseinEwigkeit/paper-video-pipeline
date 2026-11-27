import { Composition } from "remotion";
import { Full, Part } from "./film/Full";
import { FPS, H, W } from "./film/theme";
import { FULL_FRAMES } from "./film/vo";

// 1280x720 design canvas; deliver 1080p with --scale=1.5
export const RemotionRoot: React.FC = () => (
  <>
    <Composition id="Full" component={Full} durationInFrames={FULL_FRAMES} fps={FPS} width={W} height={H} />
    <Composition id="Clip" component={Part} defaultProps={{ from: 0 }} durationInFrames={FULL_FRAMES} fps={FPS} width={W} height={H} />
  </>
);
