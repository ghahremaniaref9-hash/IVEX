import "./style.css";
import { startScene } from "./gl";
import "./form";

const canvas = document.querySelector<HTMLCanvasElement>("#gl");
if (canvas) {
  try {
    if (startScene(canvas)) document.documentElement.classList.add("gl-on");
  } catch (error) {
    console.error(error);
  }
}

// Nav WhatsApp CTA: the mono label decodes from random glyphs on hover/focus.
const GLYPHS = "ABCDEFGHJKLMNOPRSTUVYZ0123456789#*+/<>";
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

document.querySelectorAll<HTMLAnchorElement>(".ivx-scramble").forEach((link) => {
  const label = link.getAttribute("aria-label") ?? "";
  const text = link.querySelector<HTMLElement>("[data-scramble]");
  if (!text || !label) return;
  let timer = 0;
  const decode = () => {
    if (reduceMotion.matches) return;
    window.clearInterval(timer);
    const total = 14;
    let frame = 0;
    timer = window.setInterval(() => {
      frame += 1;
      const settled = Math.floor((frame / total) * label.length);
      let next = "";
      for (let i = 0; i < label.length; i += 1) {
        const ch = label.charAt(i);
        next += i < settled || ch === " " || ch === "'" ? ch : GLYPHS.charAt(Math.floor(Math.random() * GLYPHS.length));
      }
      if (frame >= total) {
        next = label;
        window.clearInterval(timer);
      }
      text.textContent = next;
    }, 34);
  };
  link.addEventListener("pointerenter", decode);
  link.addEventListener("focus", decode);
});
