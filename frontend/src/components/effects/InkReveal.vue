<!--
  InkReveal.vue
  进入视口时以"墨水溶解"方式出现：
  - 用 SVG <feTurbulence> + <feDisplacementMap> 把元素边缘做成湍流形状
  - 通过 filter 让透明度沿噪声纹理逐步显现
  - IntersectionObserver 控制触发；2.5s 兜底强制显示，避免任何边缘情况下永远不显示
-->
<template>
  <div
    ref="root"
    class="ink-reveal"
    :class="{ 'is-visible': visible }"
    :style="cssVars"
  >
    <!-- 内联 SVG filter，作用于子元素 -->
    <svg width="0" height="0" class="ink-reveal__svg" aria-hidden="true">
      <defs>
        <filter :id="filterId" x="-20%" y="-20%" width="140%" height="140%">
          <feTurbulence
            type="fractalNoise"
            :baseFrequency="frequency"
            numOctaves="2"
            :seed="seed"
            stitchTiles="stitch"
          />
          <feDisplacementMap
            in="SourceGraphic"
            scale="0"
            xChannelSelector="R"
            yChannelSelector="G"
          >
            <animate
              v-if="animateDisplacement"
              attributeName="scale"
              :from="displacementFrom"
              to="0"
              :dur="`${duration}ms`"
              fill="freeze"
              :begin="visible ? '0s' : 'indefinite'"
            />
          </feDisplacementMap>
        </filter>
      </defs>
    </svg>

    <div
      class="ink-reveal__inner"
      :style="{ filter: `url(#${filterId})` }"
    >
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';

const props = withDefaults(defineProps<{
  delay?: number;            /* 进入后延迟 (ms) */
  duration?: number;         /* 溶解时长 (ms) */
  threshold?: number;        /* 视口可见比例 */
  once?: boolean;            /* 是否仅触发一次 */
  frequency?: number;        /* 噪声频率：越小颗粒越大（更像墨晕） */
  displacementFrom?: number; /* 初始位移强度（像素） */
  animateDisplacement?: boolean;
}>(), {
  delay: 0,
  duration: 1100,
  threshold: 0.15,
  once: true,
  frequency: 0.012,
  displacementFrom: 28,
  animateDisplacement: true,
});

/* 每实例分配独立 filter id，避免多实例冲突 */
let _seed = 1;
const filterId = `ink-reveal-${Math.floor(Math.random() * 1e6).toString(36)}`;
const seed = ref(_seed++);
const root = ref<HTMLElement | null>(null);
const visible = ref(false);
let observer: IntersectionObserver | null = null;
let timer: number | null = null;
let fallbackTimer: number | null = null;

const cssVars = computed(() => ({
  '--ink-reveal-duration': `${props.duration}ms`,
} as Record<string, string>));

onMounted(() => {
  if (!root.value) return;
  /* 减少动效偏好：直接显示 */
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    visible.value = true;
    return;
  }
  observer = new IntersectionObserver((entries) => {
    for (const e of entries) {
      if (e.isIntersecting) {
        if (timer) window.clearTimeout(timer);
        timer = window.setTimeout(() => { visible.value = true; }, props.delay);
        if (props.once && observer) observer.disconnect();
      } else if (!props.once) {
        visible.value = false;
      }
    }
  }, { threshold: props.threshold });
  observer.observe(root.value);

  /* 兜底：若 2.5s 后仍未触发可见，强制显示。
     避免极端布局下 (display:contents/0×0 box 等) IntersectionObserver 不回调导致永远 opacity:0 */
  fallbackTimer = window.setTimeout(() => {
    if (!visible.value) visible.value = true;
  }, 2500);
});

onBeforeUnmount(() => {
  if (observer) observer.disconnect();
  if (timer) window.clearTimeout(timer);
  if (fallbackTimer) window.clearTimeout(fallbackTimer);
});
</script>

<style scoped>
/* 注意：根元素必须有 box，IntersectionObserver 才能感知可见性，
   因此不能用 display: contents */
.ink-reveal {
  display: block;
  width: 100%;
}
.ink-reveal__inner {
  opacity: 0;
  transform: translateY(14px);
  transition:
    opacity var(--ink-reveal-duration) var(--ease-ink, cubic-bezier(0.22, 1, 0.36, 1)),
    transform var(--ink-reveal-duration) var(--ease-ink, cubic-bezier(0.22, 1, 0.36, 1));
  will-change: opacity, transform, filter;
}
.ink-reveal.is-visible .ink-reveal__inner {
  opacity: 1;
  transform: translateY(0);
}
.ink-reveal__svg {
  position: absolute;
  width: 0;
  height: 0;
}

@media (prefers-reduced-motion: reduce) {
  .ink-reveal__inner {
    opacity: 1 !important;
    transform: none !important;
    filter: none !important;
  }
}
</style>
