import { Composition } from "remotion";
import edit from "./soy/edit.json";
import { SoyOverlay } from "./soy/Overlay";
import { SoyPreview } from "./soy/Preview";

export const RemotionRoot: React.FC = () => {
  const common = {
    durationInFrames: edit.durationInFrames,
    fps: edit.fps,
    width: 1080,
    height: 1920,
  };
  return (
    <>
      <Composition id="SoyPreview" component={SoyPreview} {...common} />
      <Composition id="SoyOverlay" component={SoyOverlay} {...common} />
    </>
  );
};
