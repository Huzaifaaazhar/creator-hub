import type { Caption } from "@remotion/captions";
import { createTikTokStyleCaptions } from "@remotion/captions";
import React, { useMemo } from "react";
import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CAPTION_CENTER_Y, CREAM, FONT, MAROON, NAVY, RED } from "./theme";

// Word-timed captions: the spoken word turns red, the rest stay navy, on a cream plate with a maroon edge.
export const Captions: React.FC<{ captions: Caption[] }> = ({ captions }) => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const pages = useMemo(
    () => createTikTokStyleCaptions({ captions, combineTokensWithinMilliseconds: 450 }).pages,
    [captions],
  );
  const t = (frame / fps) * 1000;
  const page = pages.find((p) => t >= p.startMs && t < p.startMs + p.durationMs);
  if (!page) return null;

  const local = ((t - page.startMs) / 1000) * fps;
  const pop = interpolate(local, [0, 3], [0.94, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.2, 1, 0.3, 1),
  });
  const fade = interpolate(local, [0, 2], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        width,
        top: CAPTION_CENTER_Y,
        display: "flex",
        justifyContent: "center",
        translate: "0 -50%",
      }}
    >
      <div
        style={{
          scale: pop,
          opacity: fade,
          maxWidth: 940,
          background: CREAM,
          border: `5px solid ${MAROON}`,
          borderRadius: 18,
          boxShadow: `0 8px 0 ${MAROON}`,
          padding: "16px 30px 10px",
          fontFamily: FONT,
          fontSize: 66,
          lineHeight: 1.12,
          textAlign: "center",
          textTransform: "uppercase",
          whiteSpace: "pre-wrap",
          color: NAVY,
        }}
      >
        {page.tokens.map((tok) => {
          const active = t >= tok.fromMs && t < tok.toMs;
          return (
            <span key={tok.fromMs} style={{ color: active ? RED : NAVY }}>
              {tok.text}
            </span>
          );
        })}
      </div>
    </div>
  );
};
