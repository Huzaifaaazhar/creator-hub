import { Video } from "@remotion/media";
import React from "react";
import { AbsoluteFill, staticFile } from "remotion";
import { SoyOverlay } from "./Overlay";

// Studio preview: low-res base cut + the overlay, so the whole edit can be checked in the browser.
export const SoyPreview: React.FC = () => (
  <AbsoluteFill style={{ background: "#000" }}>
    <Video src={staticFile("soy_base_preview.mp4")} style={{ width: "100%", height: "100%" }} objectFit="cover" />
    <SoyOverlay />
  </AbsoluteFill>
);
