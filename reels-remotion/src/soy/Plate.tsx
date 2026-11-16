import React from "react";
import { Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { CREAM, FONT, MAROON, NAVY, RED, STICKER_TOP } from "./theme";

export type Seg = { text: string; color: "red" | "maroon" | "navy" };
export type Line = { segs: Seg[]; size: number };
export type StickerData = {
  id: string;
  t0: number;
  t1: number;
  top?: number;
  lines?: Line[];
  count?: { to: number; label: string; rollSeconds: number };
};

const COLORS = { red: RED, maroon: MAROON, navy: NAVY };

const enter = (frame: number) =>
  interpolate(frame, [0, 5], [0, 1], { extrapolateRight: "clamp", easing: Easing.bezier(0.2, 1, 0.3, 1) });

const Shell: React.FC<{ top: number; children: React.ReactNode }> = ({ top, children }) => {
  const frame = useCurrentFrame();
  const { width } = useVideoConfig();
  const k = enter(frame);
  return (
    <div style={{ position: "absolute", left: 0, width, top, display: "flex", justifyContent: "center", opacity: k }}>
      <div
        style={{
          translate: `0 ${(1 - k) * -26}px`,
          maxWidth: 960,
          background: CREAM,
          border: `6px solid ${MAROON}`,
          borderRadius: 22,
          boxShadow: `0 10px 0 ${MAROON}`,
          padding: "26px 40px 20px",
          fontFamily: FONT,
          textAlign: "center",
          textTransform: "uppercase",
        }}
      >
        {children}
        <div style={{ height: 10, marginTop: 14, background: RED, borderRadius: 5 }} />
      </div>
    </div>
  );
};

export const Plate: React.FC<{ s: StickerData }> = ({ s }) => (
  <Shell top={s.top ?? STICKER_TOP}>
    {(s.lines ?? []).map((l, i) => (
      <div key={i} style={{ fontSize: l.size, lineHeight: 1.08 }}>
        {l.segs.map((g, j) => (
          <span key={j} style={{ color: COLORS[g.color] }}>
            {g.text}
          </span>
        ))}
      </div>
    ))}
  </Shell>
);

// Score counter for the "can you hit 850?" beat. Rolls up fast, then settles (no bounce).
export const CountPlate: React.FC<{ s: StickerData }> = ({ s }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const c = s.count!;
  const v = Math.round(
    interpolate(frame, [4, 4 + c.rollSeconds * fps], [0, c.to], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.3, 0.1, 0.05, 1),
    }),
  );
  return (
    <Shell top={s.top ?? STICKER_TOP}>
      <div style={{ fontSize: 56, color: NAVY, lineHeight: 1.1 }}>{c.label}</div>
      <div style={{ fontSize: 190, color: RED, lineHeight: 1.05 }}>{v}</div>
    </Shell>
  );
};
