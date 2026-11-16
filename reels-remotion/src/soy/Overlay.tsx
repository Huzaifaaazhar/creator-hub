import type { Caption } from "@remotion/captions";
import React from "react";
import { AbsoluteFill, Sequence, useVideoConfig } from "remotion";
import edit from "./edit.json";
import { Captions } from "./Captions";
import { CountPlate, Plate, type StickerData } from "./Plate";

// Transparent graphics layer: stickers + captions. Final video = base footage + this layer.
export const SoyOverlay: React.FC = () => {
  const { fps } = useVideoConfig();
  return (
    <AbsoluteFill>
      {(edit.stickers as StickerData[]).map((s) => (
        <Sequence
          key={s.id}
          name={`Sticker ${s.id}`}
          from={Math.round(s.t0 * fps)}
          durationInFrames={Math.max(1, Math.round((s.t1 - s.t0) * fps))}
        >
          {s.count ? <CountPlate s={s} /> : <Plate s={s} />}
        </Sequence>
      ))}
      <Captions captions={edit.captions as Caption[]} />
    </AbsoluteFill>
  );
};
