import * as THREE from "three";
import { X_EDGE, X_FILL } from "./x-points";

// One fixed WebGL layer behind the page. A single particle cloud morphs between
// brand shapes as the visitor scrolls through sections marked with
// data-shape="helix|cloud|ring|stairs|mark" (+ optional data-side="left|center|right").
// The cursor pushes particles aside; they spring back on their own.

const SHAPES = ["helix", "cloud", "ring", "stairs", "mark"] as const;
type Shape = (typeof SHAPES)[number];

// Rough visual width of each shape in world units, for fitting narrow screens.
const SHAPE_WIDTH: Record<Shape, number> = { helix: 3.4, cloud: 5.6, ring: 5.0, stairs: 7.4, mark: 3.9 };
const SHAPE_SPIN: Record<Shape, number> = { helix: 0.32, cloud: 0.07, ring: 0, stairs: 0, mark: 0 };
const SHAPE_SWAY: Record<Shape, number> = { helix: 0, cloud: 0, ring: 0.3, stairs: 0.28, mark: 0.3 };

const FOV = 45;
const CAM_Z = 10;

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const rand = mulberry32(20221);
const jitter = (s: number) => (rand() + rand() + rand() - 1.5) * (s / 1.5);

function set(out: Float32Array, i: number, x: number, y: number, z: number) {
  out[i * 3] = x;
  out[i * 3 + 1] = y;
  out[i * 3 + 2] = z;
}

function helix(out: Float32Array, i: number) {
  const H = 7;
  const R = 1.25;
  const turns = 3.2;
  const r = rand();
  if (r < 0.7) {
    const phase = rand() < 0.5 ? 0 : Math.PI;
    const u = rand();
    const a = u * turns * Math.PI * 2 + phase;
    const rr = R + jitter(0.09);
    set(out, i, Math.cos(a) * rr + jitter(0.05), (u - 0.5) * H + jitter(0.05), Math.sin(a) * rr + jitter(0.05));
  } else if (r < 0.9) {
    const k = Math.floor(rand() * 34);
    const u = (k + 0.5) / 34;
    const a = u * turns * Math.PI * 2;
    const s = rand() * 2 - 1;
    set(out, i, Math.cos(a) * R * s + jitter(0.03), (u - 0.5) * H + jitter(0.03), Math.sin(a) * R * s + jitter(0.03));
  } else {
    // glitter dissolving off the strands
    const u = rand();
    const a = rand() * Math.PI * 2;
    const rr = R + 0.3 + rand() * 1.5;
    set(out, i, Math.cos(a) * rr, (u - 0.5) * H * 1.1, Math.sin(a) * rr);
  }
}

function cloud(out: Float32Array, i: number) {
  const u = rand() * 2 - 1;
  const phi = rand() * Math.PI * 2;
  const s = Math.sqrt(1 - u * u);
  const r = rand() < 0.82 ? 2.7 + jitter(0.14) : Math.cbrt(rand()) * 2.4;
  set(out, i, Math.cos(phi) * s * r, u * r, Math.sin(phi) * s * r);
}

function ring(out: Float32Array, i: number) {
  if (rand() < 0.6) {
    const theta = rand() * Math.PI * 2;
    const phi = rand() * Math.PI * 2;
    const R = 2.3;
    const tube = 0.08 + rand() * 0.06;
    set(out, i, (R + tube * Math.cos(phi)) * Math.cos(theta), (R + tube * Math.cos(phi)) * Math.sin(theta), tube * Math.sin(phi));
    return;
  }
  // a phone outline standing in the ring light
  const w = 1.4;
  const h = 2.8;
  const rc = 0.28;
  const t = rand() * 2 * (w + h);
  let x: number;
  let y: number;
  if (t < w) [x, y] = [t - w / 2, h / 2];
  else if (t < w + h) [x, y] = [w / 2, h / 2 - (t - w)];
  else if (t < 2 * w + h) [x, y] = [w / 2 - (t - w - h), -h / 2];
  else [x, y] = [-w / 2, -h / 2 + (t - 2 * w - h)];
  const cx = Math.sign(x) * (w / 2 - rc);
  const cy = Math.sign(y) * (h / 2 - rc);
  if (Math.abs(x) > w / 2 - rc && Math.abs(y) > h / 2 - rc) {
    const a = Math.atan2(y - cy, x - cx);
    x = cx + Math.cos(a) * rc;
    y = cy + Math.sin(a) * rc;
  }
  if (rand() < 0.12) {
    // a few glints on the glass
    x = (rand() - 0.5) * w * 0.9;
    y = (rand() - 0.5) * h * 0.9;
  }
  set(out, i, x + jitter(0.02), y + jitter(0.02), 0.35 + jitter(0.04));
}

function boxPoint(cx: number, by: number, w: number, h: number, d: number): [number, number, number] {
  const x0 = cx - w / 2;
  const z0 = -d / 2;
  if (rand() < 0.55) {
    // edges read as crisp glass blocks
    const e = Math.floor(rand() * 12);
    const t = rand();
    const ax = e < 4 ? 0 : e < 8 ? 1 : 2;
    const k = e % 4;
    const bx = k & 1;
    const bz = (k >> 1) & 1;
    if (ax === 0) return [x0 + t * w, by + bx * h, z0 + bz * d];
    if (ax === 1) return [x0 + bx * w, by + t * h, z0 + bz * d];
    return [x0 + bx * w, by + bz * h, z0 + t * d];
  }
  const f = Math.floor(rand() * 6);
  const u = rand();
  const v = rand();
  if (f === 0) return [x0 + u * w, by + v * h, z0];
  if (f === 1) return [x0 + u * w, by + v * h, z0 + d];
  if (f === 2) return [x0, by + u * h, z0 + v * d];
  if (f === 3) return [x0 + w, by + u * h, z0 + v * d];
  if (f === 4) return [x0 + u * w, by + h, z0 + v * d];
  return [x0 + u * w, by, z0 + v * d];
}

function stairs(out: Float32Array, i: number) {
  const r = rand();
  if (r < 0.12) {
    // the beam of light climbing through the steps
    const t = rand();
    set(out, i, -5.6 + t * 8.9 + jitter(0.04), -1.5 + t * 3.4 + jitter(0.04), jitter(0.04));
    return;
  }
  if (r < 0.18) {
    // the burst where it lands
    const a = rand() * Math.PI * 2;
    const b = rand() * Math.PI - Math.PI / 2;
    const d = Math.pow(rand(), 0.6) * 1.2;
    set(out, i, 3.4 + Math.cos(a) * Math.cos(b) * d, 1.95 + Math.sin(b) * d, Math.sin(a) * Math.cos(b) * d);
    return;
  }
  const k = rand();
  const box = k < 0.27 ? { x: -2.2, h: 1.3 } : k < 0.6 ? { x: 0, h: 2.3 } : { x: 2.2, h: 3.3 };
  const [x, y, z] = boxPoint(box.x, -2.1, 1.3, box.h, 1.3);
  set(out, i, x + jitter(0.015), y + jitter(0.015), z + jitter(0.015));
}

// The X of the IVEX logo as a thin glass slab: outlines on both faces, a filled core.
function mark(out: Float32Array, i: number) {
  const depth = 0.3;
  if (rand() < 0.58) {
    const k = Math.floor(rand() * (X_EDGE.length / 2)) * 2;
    const z = (rand() < 0.5 ? -depth : depth) + jitter(0.02);
    set(out, i, X_EDGE[k] + jitter(0.012), X_EDGE[k + 1] + jitter(0.012), z);
    return;
  }
  const k = Math.floor(rand() * (X_FILL.length / 2)) * 2;
  set(out, i, X_FILL[k] + jitter(0.02), X_FILL[k + 1] + jitter(0.02), (rand() - 0.5) * depth * 2);
}

const BUILDERS: Record<Shape, (out: Float32Array, i: number) => void> = { helix, cloud, ring, stairs, mark };

const vertexShader = /* glsl */ `
  uniform float uTime;
  uniform float uIntro;
  uniform int uFrom;
  uniform int uTo;
  uniform float uMix;
  uniform vec3 uFromOffset;
  uniform vec3 uToOffset;
  uniform float uFromScale;
  uniform float uToScale;
  uniform float uFromSpin;
  uniform float uToSpin;
  uniform float uFromSway;
  uniform float uToSway;
  uniform vec3 uMouse;
  uniform float uMouseForce;
  uniform float uSize;
  uniform float uPixelRatio;

  attribute vec3 aHelix;
  attribute vec3 aCloud;
  attribute vec3 aRing;
  attribute vec3 aStairs;
  attribute vec3 aMark;
  attribute float aRand;
  attribute float aSize;
  attribute float aTone;

  varying float vTone;
  varying float vAlpha;

  vec3 shapePos(int i) {
    if (i == 0) return aHelix;
    if (i == 1) return aCloud;
    if (i == 2) return aRing;
    if (i == 3) return aStairs;
    return aMark;
  }

  vec3 rotY(vec3 p, float a) {
    float c = cos(a);
    float s = sin(a);
    return vec3(c * p.x + s * p.z, p.y, -s * p.x + c * p.z);
  }

  void main() {
    float sway = sin(uTime * 0.4);
    vec3 a = rotY(shapePos(uFrom), uTime * uFromSpin + sway * uFromSway) * uFromScale + uFromOffset;
    vec3 b = rotY(shapePos(uTo), uTime * uToSpin + sway * uToSway) * uToScale + uToOffset;

    float m = clamp((uMix - aRand * 0.35) / 0.65, 0.0, 1.0);
    m = m * m * (3.0 - 2.0 * m);
    vec3 dir = normalize(vec3(sin(aRand * 41.0), cos(aRand * 23.0), sin(aRand * 17.0)) + 1e-4);
    vec3 p = mix(a, b, m) + dir * sin(m * 3.14159) * 0.9;

    p += vec3(sin(uTime * 0.7 + aRand * 30.0), cos(uTime * 0.6 + aRand * 20.0), sin(uTime * 0.5 + aRand * 10.0)) * 0.03;

    float intro = 1.0 - pow(1.0 - clamp(uIntro * 1.4 - aRand * 0.4, 0.0, 1.0), 3.0);
    p = mix(p * 2.2 + dir * 5.0, p, intro);

    vec2 d = p.xy - uMouse.xy;
    float dist = length(d);
    float push = (1.0 - smoothstep(0.0, 1.7, dist)) * uMouseForce;
    p.xy += (d / max(dist, 1e-3)) * push * 0.95;
    p.z += push * 0.7;

    vec4 mv = modelViewMatrix * vec4(p, 1.0);
    gl_Position = projectionMatrix * mv;
    gl_PointSize = uSize * aSize * uPixelRatio * (8.0 / -mv.z);

    vTone = aTone;
    vAlpha = (0.45 + 0.55 * aRand) * smoothstep(-22.0, -7.0, mv.z) * intro;
  }
`;

const fragmentShader = /* glsl */ `
  uniform vec3 uColorA;
  uniform vec3 uColorB;
  uniform vec3 uColorC;
  uniform float uOpacity;
  varying float vTone;
  varying float vAlpha;

  void main() {
    float d = length(gl_PointCoord - 0.5);
    float core = smoothstep(0.5, 0.0, d);
    float alpha = core * core * vAlpha * uOpacity;
    if (alpha < 0.004) discard;
    vec3 col = mix(uColorA, uColorB, smoothstep(0.0, 0.75, vTone));
    col = mix(col, uColorC, smoothstep(0.88, 1.0, vTone));
    gl_FragColor = vec4(col, alpha);
  }
`;

type Chapter = { el: HTMLElement; shape: number; side: number; opacity: number; x: number; y: number; scaleCap: number };

export function startScene(canvas: HTMLCanvasElement): boolean {
  let renderer: THREE.WebGLRenderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas, antialias: false, alpha: true, powerPreference: "high-performance" });
  } catch {
    return false;
  }

  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const finePointer = window.matchMedia("(pointer: fine)").matches;
  const small = Math.min(window.innerWidth, window.innerHeight) < 700;
  const count = small ? 9000 : 20000;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(FOV, 1, 0.1, 100);
  camera.position.set(0, 0, CAM_Z);

  const geometry = new THREE.BufferGeometry();
  const dustShare = 0.09;
  const shapeArrays = SHAPES.map(() => new Float32Array(count * 3));
  const rnd = new Float32Array(count);
  const size = new Float32Array(count);
  const tone = new Float32Array(count);
  for (let i = 0; i < count; i += 1) {
    const isDust = i < count * dustShare;
    if (isDust) {
      const x = (rand() - 0.5) * 20;
      const y = (rand() - 0.5) * 13;
      const z = -7 + rand() * 9;
      shapeArrays.forEach((arr) => set(arr, i, x, y, z));
    } else {
      SHAPES.forEach((shape, s) => BUILDERS[shape](shapeArrays[s], i));
    }
    rnd[i] = rand();
    size[i] = isDust ? 0.5 + rand() * 0.6 : 0.65 + Math.pow(rand(), 3) * 1.6;
    tone[i] = isDust ? 0.2 + rand() * 0.4 : Math.pow(rand(), 0.7);
  }
  // position is required by three for bounds; the shader reads the shape attributes
  geometry.setAttribute("position", new THREE.BufferAttribute(shapeArrays[0], 3));
  geometry.setAttribute("aHelix", new THREE.BufferAttribute(shapeArrays[0], 3));
  geometry.setAttribute("aCloud", new THREE.BufferAttribute(shapeArrays[1], 3));
  geometry.setAttribute("aRing", new THREE.BufferAttribute(shapeArrays[2], 3));
  geometry.setAttribute("aStairs", new THREE.BufferAttribute(shapeArrays[3], 3));
  geometry.setAttribute("aMark", new THREE.BufferAttribute(shapeArrays[4], 3));
  geometry.setAttribute("aRand", new THREE.BufferAttribute(rnd, 1));
  geometry.setAttribute("aSize", new THREE.BufferAttribute(size, 1));
  geometry.setAttribute("aTone", new THREE.BufferAttribute(tone, 1));
  geometry.boundingSphere = new THREE.Sphere(new THREE.Vector3(), 30);

  const uniforms = {
    uTime: { value: 0 },
    uIntro: { value: reduceMotion.matches ? 1 : 0 },
    uFrom: { value: 0 },
    uTo: { value: 0 },
    uMix: { value: 0 },
    uFromOffset: { value: new THREE.Vector3() },
    uToOffset: { value: new THREE.Vector3() },
    uFromScale: { value: 1 },
    uToScale: { value: 1 },
    uFromSpin: { value: 0 },
    uToSpin: { value: 0 },
    uFromSway: { value: 0 },
    uToSway: { value: 0 },
    uMouse: { value: new THREE.Vector3(99, 99, 0) },
    uMouseForce: { value: 0 },
    uSize: { value: small ? 4.4 : 3.9 },
    uPixelRatio: { value: 1 },
    uColorA: { value: new THREE.Color("#1f7a3f") },
    uColorB: { value: new THREE.Color("#b6ef2a") },
    uColorC: { value: new THREE.Color("#f3ffd2") },
    uOpacity: { value: 0.85 },
  };

  const material = new THREE.ShaderMaterial({
    uniforms,
    vertexShader,
    fragmentShader,
    transparent: true,
    depthWrite: false,
    blending: THREE.AdditiveBlending,
  });
  scene.add(new THREE.Points(geometry, material));

  const chapters: Chapter[] = Array.from(document.querySelectorAll<HTMLElement>("[data-shape]")).map((el) => {
    const shape = Math.max(0, SHAPES.indexOf((el.dataset.shape ?? "helix") as Shape));
    const side = el.dataset.side === "right" ? 1 : el.dataset.side === "left" ? -1 : 0;
    const opacity = el.dataset.dim === "true" ? 0.6 : 0.95;
    // optional per-section placement: data-x (fraction of half width), data-y (world units), data-scale (cap)
    const num = (v: string | undefined, fallback: number) => (v !== undefined && Number.isFinite(Number(v)) ? Number(v) : fallback);
    return { el, shape, side, opacity, x: num(el.dataset.x, 0.42), y: num(el.dataset.y, 0), scaleCap: num(el.dataset.scale, 1.1) };
  });
  if (chapters.length === 0) return false;

  let width = 0;
  let height = 0;
  const resize = () => {
    width = window.innerWidth;
    height = window.innerHeight;
    const dpr = Math.min(window.devicePixelRatio || 1, small ? 1.5 : 1.75);
    renderer.setPixelRatio(dpr);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    uniforms.uPixelRatio.value = dpr;
  };
  resize();
  window.addEventListener("resize", resize);

  const placement = (c: Chapter) => {
    const halfH = Math.tan(THREE.MathUtils.degToRad(FOV / 2)) * CAM_Z;
    const halfW = halfH * camera.aspect;
    const shape = SHAPES[c.shape];
    if (camera.aspect < 0.9) {
      const scale = THREE.MathUtils.clamp((halfW * 1.9) / SHAPE_WIDTH[shape], 0.4, 1);
      return { offset: new THREE.Vector3(0, halfH * 0.12, -1), scale };
    }
    const scale = THREE.MathUtils.clamp((halfW * 0.95) / SHAPE_WIDTH[shape], 0.55, c.scaleCap);
    return { offset: new THREE.Vector3(c.side * halfW * c.x, c.y, 0), scale };
  };

  const slots = {
    from: { shape: uniforms.uFrom, offset: uniforms.uFromOffset, scale: uniforms.uFromScale, spin: uniforms.uFromSpin, sway: uniforms.uFromSway },
    to: { shape: uniforms.uTo, offset: uniforms.uToOffset, scale: uniforms.uToScale, spin: uniforms.uToSpin, sway: uniforms.uToSway },
  };
  const applyChapter = (slot: (typeof slots)["from"], c: Chapter) => {
    const { offset, scale } = placement(c);
    const shape = SHAPES[c.shape];
    slot.shape.value = c.shape;
    slot.offset.value.copy(offset);
    slot.scale.value = scale;
    slot.spin.value = SHAPE_SPIN[shape];
    slot.sway.value = SHAPE_SWAY[shape];
  };

  // Which two chapters straddle the viewport centre, and how far between them.
  const updateScroll = () => {
    const vc = height / 2;
    const centers = chapters.map((c) => {
      const r = c.el.getBoundingClientRect();
      return r.top + r.height / 2;
    });
    let i = -1;
    for (let k = 0; k < centers.length; k += 1) if (centers[k] <= vc) i = k;
    let from = Math.max(0, i);
    let to = from;
    let mix = 0;
    if (i >= 0 && i < chapters.length - 1) {
      const f = (vc - centers[i]) / Math.max(1, centers[i + 1] - centers[i]);
      mix = THREE.MathUtils.smoothstep(f, 0.28, 0.72);
      to = i + 1;
    }
    if (mix >= 0.999) {
      from = to;
      mix = 0;
    }
    applyChapter(slots.from, chapters[from]);
    applyChapter(slots.to, chapters[to]);
    uniforms.uMix.value = mix;
    const opacity = THREE.MathUtils.lerp(chapters[from].opacity, chapters[to].opacity, mix);
    uniforms.uOpacity.value = camera.aspect < 0.9 ? opacity * 0.85 : opacity;
  };

  const pointer = new THREE.Vector2(0, 0);
  const pointerTarget = new THREE.Vector2(0, 0);
  const raycaster = new THREE.Raycaster();
  const plane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
  const hit = new THREE.Vector3();
  let mouseActive = false;
  let lastMove = 0;
  if (finePointer) {
    window.addEventListener(
      "pointermove",
      (e) => {
        pointerTarget.set((e.clientX / width) * 2 - 1, -(e.clientY / height) * 2 + 1);
        mouseActive = true;
        lastMove = performance.now();
      },
      { passive: true },
    );
    document.addEventListener("pointerleave", () => {
      mouseActive = false;
    });
  }

  const clock = { t: 0 };
  let last = performance.now();
  let visible = !document.hidden;
  document.addEventListener("visibilitychange", () => {
    visible = !document.hidden;
    if (visible) last = performance.now();
  });
  const frame = (now: number) => {
    requestAnimationFrame(frame);
    if (!visible) return;
    const dt = Math.min(0.05, (now - last) / 1000);
    last = now;
    const still = reduceMotion.matches;
    if (!still) {
      clock.t += dt;
      uniforms.uIntro.value = Math.min(1, uniforms.uIntro.value + dt / 2.4);
    } else {
      uniforms.uIntro.value = 1;
    }
    uniforms.uTime.value = clock.t;

    pointer.lerp(pointerTarget, 0.06);
    if (!still) {
      camera.position.x = pointer.x * 0.45;
      camera.position.y = pointer.y * 0.3;
      camera.lookAt(0, 0, 0);
    }

    const engaged = !still && mouseActive && now - lastMove < 2500;
    if (engaged) {
      raycaster.setFromCamera(pointerTarget, camera);
      if (raycaster.ray.intersectPlane(plane, hit)) uniforms.uMouse.value.lerp(hit, 0.35);
    }
    uniforms.uMouseForce.value += ((engaged ? 1 : 0) - uniforms.uMouseForce.value) * 0.06;

    updateScroll();
    renderer.render(scene, camera);
  };
  requestAnimationFrame(frame);
  return true;
}
