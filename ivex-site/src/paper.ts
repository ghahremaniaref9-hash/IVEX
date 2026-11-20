// Editoryal kağıt (light theme only): soft light that follows the cursor and a
// slow drift of the IVEX watermark while scrolling. Respects reduced motion.

const root = document.documentElement;
const mark = document.querySelector<HTMLElement>(".ipb-mark");
const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

if (root.dataset.theme === "light" && !reduce.matches) {
  let raf = 0;
  let px = 0.62;
  let py = 0.18;

  const flush = () => {
    raf = 0;
    root.style.setProperty("--ipb-px", `${(px * 100).toFixed(2)}%`);
    root.style.setProperty("--ipb-py", `${(py * 100).toFixed(2)}%`);
  };

  const drift = () => {
    if (!mark) return;
    const max = root.scrollHeight - window.innerHeight;
    const progress = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0;
    mark.style.setProperty("--ipb-drift", `${(-progress * 72).toFixed(1)}px`);
  };

  window.addEventListener(
    "pointermove",
    (event) => {
      px = event.clientX / Math.max(1, window.innerWidth);
      py = event.clientY / Math.max(1, window.innerHeight);
      if (!raf) raf = requestAnimationFrame(flush);
    },
    { passive: true },
  );
  window.addEventListener("scroll", drift, { passive: true });
  drift();
}
