import { loadFont } from "@remotion/fonts";
import { continueRender, delayRender, staticFile } from "remotion";

// Palette requested for all text. Plates are warm cream so the three text colours stay readable on any footage.
export const MAROON = "#6E0C16";
export const RED = "#A8202B";
export const NAVY = "#101D3A";
export const CREAM = "#F7EEDB";

export const FONT = "Graduate, serif";

const handle = delayRender("Loading Graduate");
loadFont({
  family: "Graduate",
  url: staticFile("fonts/Graduate-Regular.ttf"),
  weight: "400",
})
  .then(() => continueRender(handle))
  .catch((e) => {
    throw e;
  });

// layout in 1080x1920 coordinates (rendered at scale 2 -> 2160x3840)
export const CAPTION_CENTER_Y = 1342; // plate sits just under the chin
export const STICKER_TOP = 330; // below Instagram's top UI
