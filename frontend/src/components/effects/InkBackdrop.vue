<!--
  InkBackdrop.vue
  全屏 WebGL 着色器：模拟水墨在宣纸上的缓慢晕染。
  - 使用分形布朗运动 (fbm) + 域扭曲 (domain warp) 生成低频墨晕
  - 叠加宣纸颗粒纹理与远山轮廓暗示
  - 自动适配 DPR 与窗口尺寸
  - 监听 prefers-reduced-motion，运动学降级为静态画面
  - 切到后台时暂停渲染，节省电量
-->
<template>
  <div class="ink-backdrop" aria-hidden="true">
    <canvas ref="canvasRef" class="ink-canvas" />
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';

const canvasRef = ref<HTMLCanvasElement | null>(null);

let gl: WebGLRenderingContext | null = null;
let program: WebGLProgram | null = null;
let raf = 0;
let startTs = 0;
let running = true;
let reducedMotion = false;
let resizeObs: ResizeObserver | null = null;

const VERT = `
attribute vec2 a_pos;
varying vec2 v_uv;
void main() {
  v_uv = a_pos * 0.5 + 0.5;
  gl_Position = vec4(a_pos, 0.0, 1.0);
}
`;

/* 颜色常量与 variables.css 中色板呼应：宣纸基底 / 远山黛 / 烟青 / 一抹琥珀 */
const FRAG = `
precision highp float;
varying vec2 v_uv;
uniform float u_time;
uniform vec2 u_res;
uniform float u_motion; /* 1.0=正常, 0.0=减少动效 */

/* hash & value noise */
float hash(vec2 p) {
  p = fract(p * vec2(123.34, 456.21));
  p += dot(p, p + 45.32);
  return fract(p.x * p.y);
}
float vnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  return mix(mix(a, b, u.x), mix(c, d, u.x), u.y);
}
float fbm(vec2 p) {
  float s = 0.0;
  float a = 0.5;
  mat2 r = mat2(0.8, -0.6, 0.6, 0.8);
  for (int i = 0; i < 5; i++) {
    s += a * vnoise(p);
    p = r * p * 2.02;
    a *= 0.5;
  }
  return s;
}

void main() {
  vec2 uv = v_uv;
  float aspect = u_res.x / max(u_res.y, 1.0);
  vec2 p = vec2(uv.x * aspect, uv.y);

  /* 极慢的"风"：动效降级时大幅减弱 */
  float t = u_time * 0.025 * mix(0.15, 1.0, u_motion);

  /* 域扭曲：让墨形状不规则 */
  vec2 q = vec2(fbm(p + vec2(0.0, t)),
                fbm(p + vec2(5.2, -t * 0.7)));
  vec2 r = vec2(fbm(p + 4.0 * q + vec2(1.7, 9.2) + 0.15 * t),
                fbm(p + 4.0 * q + vec2(8.3, 2.8) - 0.13 * t));
  float ink = fbm(p + 4.0 * r);

  /* 宣纸基底色 */
  vec3 paper = vec3(0.969, 0.953, 0.925); /* #f7f3ec */
  vec3 paperWarm = vec3(0.984, 0.965, 0.918);
  vec3 base = mix(paper, paperWarm, smoothstep(0.0, 1.0, uv.y));

  /* 墨色（远山黛）*/
  vec3 ink1 = vec3(0.290, 0.314, 0.353); /* #4a5260 */
  vec3 ink2 = vec3(0.486, 0.592, 0.722); /* #7c97b8 */
  /* 一抹极淡的琥珀（让画面有暖意，不至于死灰）*/
  vec3 amber = vec3(0.776, 0.604, 0.290); /* #c69a4a */

  /* 远山一笔：底部 1/3 处一条横向墨纹 */
  float mountainBand = smoothstep(0.20, 0.42, uv.y) * (1.0 - smoothstep(0.42, 0.62, uv.y));
  float mountainShape = fbm(vec2(p.x * 1.8, p.y * 6.0 + 0.3));
  float mountain = mountainBand * smoothstep(0.45, 0.65, mountainShape);

  /* 主墨晕：中高 fbm 值的部分 */
  float wash = smoothstep(0.42, 0.78, ink);
  float deepWash = smoothstep(0.62, 0.92, ink);

  /* 颗粒（宣纸纹理）：用 hash 当噪点 */
  float grain = (hash(uv * u_res * 0.5) - 0.5) * 0.025;

  vec3 col = base;
  col = mix(col, ink2, wash * 0.18);
  col = mix(col, ink1, deepWash * 0.22);
  col = mix(col, ink1 * 0.8, mountain * 0.35);
  /* 右上一点琥珀光晕，模拟落日 */
  float warm = smoothstep(0.35, 0.0, distance(uv, vec2(0.82, 0.18)));
  col = mix(col, mix(col, amber, 0.35), warm * 0.25);

  col += grain;

  /* 边缘暗角，让中央更明亮 */
  float vignette = smoothstep(1.15, 0.55, distance(uv, vec2(0.5, 0.5)));
  col *= mix(0.92, 1.0, vignette);

  gl_FragColor = vec4(col, 1.0);
}
`;

function compile(type: number, src: string): WebGLShader | null {
  if (!gl) return null;
  const s = gl.createShader(type);
  if (!s) return null;
  gl.shaderSource(s, src);
  gl.compileShader(s);
  if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) {
    console.error('[InkBackdrop] shader compile error:', gl.getShaderInfoLog(s));
    gl.deleteShader(s);
    return null;
  }
  return s;
}

function initGL(canvas: HTMLCanvasElement) {
  gl = canvas.getContext('webgl', { antialias: false, premultipliedAlpha: false }) as WebGLRenderingContext | null;
  if (!gl) return false;

  const vs = compile(gl.VERTEX_SHADER, VERT);
  const fs = compile(gl.FRAGMENT_SHADER, FRAG);
  if (!vs || !fs) return false;

  program = gl.createProgram();
  if (!program) return false;
  gl.attachShader(program, vs);
  gl.attachShader(program, fs);
  gl.linkProgram(program);
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
    console.error('[InkBackdrop] program link error:', gl.getProgramInfoLog(program));
    return false;
  }

  /* 全屏三角形：用单 strip 覆盖 NDC */
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([
    -1, -1,  3, -1,  -1, 3,
  ]), gl.STATIC_DRAW);

  const loc = gl.getAttribLocation(program, 'a_pos');
  gl.enableVertexAttribArray(loc);
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);

  gl.useProgram(program);
  return true;
}

function resize() {
  const c = canvasRef.value;
  if (!c || !gl) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 1.75);
  const w = Math.floor(c.clientWidth * dpr);
  const h = Math.floor(c.clientHeight * dpr);
  if (c.width !== w || c.height !== h) {
    c.width = w;
    c.height = h;
    gl.viewport(0, 0, w, h);
  }
}

function frame(now: number) {
  if (!running || !gl || !program) return;
  if (!startTs) startTs = now;
  resize();

  const uTime = gl.getUniformLocation(program, 'u_time');
  const uRes = gl.getUniformLocation(program, 'u_res');
  const uMotion = gl.getUniformLocation(program, 'u_motion');
  gl.uniform1f(uTime, (now - startTs) / 1000);
  gl.uniform2f(uRes, gl.drawingBufferWidth, gl.drawingBufferHeight);
  gl.uniform1f(uMotion, reducedMotion ? 0.0 : 1.0);

  gl.drawArrays(gl.TRIANGLES, 0, 3);

  /* 减少动效时降低帧率：仅每 ~250ms 重绘一次 */
  if (reducedMotion) {
    raf = window.setTimeout(() => requestAnimationFrame(frame), 250) as unknown as number;
  } else {
    raf = requestAnimationFrame(frame);
  }
}

function onVisibilityChange() {
  if (document.hidden) {
    running = false;
    if (raf) cancelAnimationFrame(raf);
  } else {
    if (!running) {
      running = true;
      startTs = 0;
      raf = requestAnimationFrame(frame);
    }
  }
}

onMounted(() => {
  const c = canvasRef.value;
  if (!c) return;
  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!initGL(c)) {
    /* WebGL 初始化失败：降级为纯色背景（CSS 背景已经是 paper 色） */
    return;
  }
  resize();
  resizeObs = new ResizeObserver(() => resize());
  resizeObs.observe(c);
  document.addEventListener('visibilitychange', onVisibilityChange);
  raf = requestAnimationFrame(frame);
});

onBeforeUnmount(() => {
  running = false;
  if (raf) cancelAnimationFrame(raf);
  if (resizeObs) resizeObs.disconnect();
  document.removeEventListener('visibilitychange', onVisibilityChange);
  if (gl && program) gl.deleteProgram(program);
  gl = null;
  program = null;
});
</script>

<style scoped>
.ink-backdrop {
  position: fixed;
  inset: 0;
  z-index: -2;            /* 位于业务层之下；#app 的 isolation 防止漏到 body 后 */
  pointer-events: none;
  overflow: hidden;
}
.ink-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}
</style>
