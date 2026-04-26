<!--
  ParticleField.vue
  细微的柔光粒子场，叠加在水墨背景之上、业务层之下：
  - Canvas 2D，自动适配 DPR
  - 数量根据屏幕面积自适应（移动端少，桌面多）
  - 缓慢上飘 + 微小的水平扰动 + 透明度呼吸
  - 减少动效偏好下，仅渲染静态粒子层（不动）
-->
<template>
  <canvas ref="canvasRef" class="particle-field" aria-hidden="true" />
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue';

interface P {
  x: number; y: number;
  vx: number; vy: number;
  r: number;          /* 半径 */
  a: number;          /* 当前透明度 */
  aMax: number;       /* 透明度上限 */
  phase: number;      /* 呼吸相位 */
  hue: number;        /* 0=暖白, 1=烟青, 2=琥珀 */
}

const canvasRef = ref<HTMLCanvasElement | null>(null);
let ctx: CanvasRenderingContext2D | null = null;
let raf = 0;
let particles: P[] = [];
let lastTs = 0;
let running = true;
let reducedMotion = false;
let resizeObs: ResizeObserver | null = null;

const COLORS = [
  'rgba(255, 248, 232, ',   /* 暖白 */
  'rgba(180, 199, 217, ',   /* 烟青 */
  'rgba(214, 178, 130, ',   /* 琥珀 */
];

function rand(min: number, max: number) {
  return min + Math.random() * (max - min);
}

function buildParticles() {
  if (!canvasRef.value) return;
  const w = canvasRef.value.clientWidth;
  const h = canvasRef.value.clientHeight;
  const area = w * h;
  /* 每 18000 px² 一个粒子，上下限保证移动/超宽屏都合理 */
  const count = Math.max(28, Math.min(110, Math.round(area / 18000)));
  particles = new Array(count).fill(0).map(() => ({
    x: rand(0, w),
    y: rand(0, h),
    vx: rand(-0.04, 0.04),
    vy: rand(-0.18, -0.04),  /* 持续上飘 */
    r: rand(0.6, 1.8),
    a: 0,
    aMax: rand(0.18, 0.55),
    phase: rand(0, Math.PI * 2),
    hue: Math.random() < 0.7 ? 0 : (Math.random() < 0.5 ? 1 : 2),
  }));
}

function resize() {
  const c = canvasRef.value;
  if (!c || !ctx) return;
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = c.clientWidth, h = c.clientHeight;
  if (c.width !== w * dpr || c.height !== h * dpr) {
    c.width = Math.floor(w * dpr);
    c.height = Math.floor(h * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    buildParticles();
  }
}

function frame(now: number) {
  if (!running || !ctx || !canvasRef.value) return;
  if (!lastTs) lastTs = now;
  const dt = Math.min(48, now - lastTs);
  lastTs = now;

  const w = canvasRef.value.clientWidth;
  const h = canvasRef.value.clientHeight;
  ctx.clearRect(0, 0, w, h);

  for (const p of particles) {
    if (!reducedMotion) {
      p.x += p.vx * dt;
      p.y += p.vy * dt * 0.6;
      p.phase += dt * 0.0014;
      /* 透明度呼吸（在 0 和 aMax 间） */
      p.a = (Math.sin(p.phase) * 0.5 + 0.5) * p.aMax;
      /* 上飘出顶部时从底部返回 */
      if (p.y < -10) {
        p.y = h + 10;
        p.x = rand(0, w);
      }
      if (p.x < -10) p.x = w + 10;
      if (p.x > w + 10) p.x = -10;
    } else {
      p.a = p.aMax * 0.5;
    }

    ctx.fillStyle = COLORS[p.hue] + p.a.toFixed(3) + ')';
    ctx.beginPath();
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    ctx.fill();
  }

  raf = requestAnimationFrame(frame);
}

function onVisibilityChange() {
  if (document.hidden) {
    running = false;
    if (raf) cancelAnimationFrame(raf);
  } else if (!running) {
    running = true;
    lastTs = 0;
    raf = requestAnimationFrame(frame);
  }
}

onMounted(() => {
  const c = canvasRef.value;
  if (!c) return;
  ctx = c.getContext('2d');
  if (!ctx) return;
  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  resize();
  buildParticles();
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
  ctx = null;
  particles = [];
});
</script>

<style scoped>
.particle-field {
  position: fixed;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: -1;            /* 介于背景与业务层之间 */
  pointer-events: none;
}
</style>
