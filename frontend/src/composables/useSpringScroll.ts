/**
 * useSpringScroll
 * 在指定容器上启用"弹簧阻尼"平滑滚动，并在边界做回弹。
 *
 * 设计要点：
 * - 仅拦截滚动到达视口顶/底时的 wheel 事件做回弹形变；正常滚动仍走 native scrollTop（保留辅助技术、键盘、触摸惯性）
 * - 平滑滚动通过对 scrollTop 做 spring 插值实现：currentY → targetY，每帧 RAF 推进
 * - 不替换 native 滚动条，不破坏 ant 的 modal/dropdown/select 等内部滚动
 * - 对触摸设备保持原生体验（触摸惯性已足够）
 */

import { onBeforeUnmount, onMounted, type Ref } from 'vue';

export interface SpringScrollOptions {
  /** 弹簧刚度，越大越快收敛 */
  stiffness?: number;
  /** 阻尼，越大越不振荡（建议 0.7~0.95） */
  damping?: number;
  /** 一次 wheel 步长系数（相对 deltaY），1 为原始速度 */
  wheelMultiplier?: number;
  /** 触发回弹形变所需的"超出量"上限（像素），实际位移会被收敛到此范围内 */
  bounceMax?: number;
  /** 边缘回弹的弹簧刚度（更快回正） */
  bounceStiffness?: number;
  /** 边缘回弹阻尼 */
  bounceDamping?: number;
  /** 是否启用（false 时一切走 native） */
  enabled?: boolean;
}

const DEFAULTS: Required<SpringScrollOptions> = {
  stiffness: 0.085,
  damping: 0.82,
  wheelMultiplier: 1.0,
  bounceMax: 80,
  bounceStiffness: 0.18,
  bounceDamping: 0.72,
  enabled: true,
};

function isTouchDevice(): boolean {
  return (typeof window !== 'undefined') && (
    'ontouchstart' in window ||
    (navigator.maxTouchPoints || 0) > 0
  );
}

function prefersReducedMotion(): boolean {
  return typeof window !== 'undefined'
    && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

/**
 * @param target 滚动容器 ref（必须是 overflow: auto/scroll 的元素）
 * @param innerTarget 用于"回弹形变"的内部包裹元素 ref（其 transform 会被设置）
 *                    若不提供，则只做平滑滚动，不做边缘回弹
 */
export function useSpringScroll(
  target: Ref<HTMLElement | null>,
  innerTarget?: Ref<HTMLElement | null>,
  opts: SpringScrollOptions = {},
) {
  const cfg = { ...DEFAULTS, ...opts };

  let rafId = 0;
  let running = false;
  let currentY = 0;     /* 当前应用的 scrollTop */
  let targetY = 0;      /* 目标 scrollTop */
  let bounceY = 0;      /* 边缘形变量：负=顶部下拉，正=底部上拉 */
  let bounceVel = 0;
  let lastTs = 0;

  /* 是否在事件中（用户主动 wheel），用于禁用平滑跟随原生滚动条 */
  let userWheeling = false;
  let wheelEndTimer: number | null = null;

  function tick(now: number) {
    if (!running) return;
    if (!lastTs) lastTs = now;
    const dt = Math.min(48, now - lastTs);
    lastTs = now;
    /* 用步长帧数补偿（基础 16.67ms） */
    const steps = Math.max(1, Math.round(dt / 16.67));

    const el = target.value;
    if (!el) { rafId = requestAnimationFrame(tick); return; }

    /* 平滑滚动主体 */
    for (let i = 0; i < steps; i++) {
      currentY += (targetY - currentY) * cfg.stiffness;
      currentY = currentY * (1 - (1 - cfg.damping) * 0.0); /* 阻尼隐含在 stiffness 收敛中 */
    }
    /* 直接写入 scrollTop（值不会触发回弹，因为 wheel 已 preventDefault） */
    if (Math.abs(targetY - currentY) < 0.1) currentY = targetY;
    el.scrollTop = currentY;

    /* 边缘回弹（spring 阻尼振子） */
    if (innerTarget?.value) {
      bounceVel += -cfg.bounceStiffness * bounceY;
      bounceVel *= cfg.bounceDamping;
      bounceY += bounceVel;
      if (Math.abs(bounceY) < 0.05 && Math.abs(bounceVel) < 0.05) {
        bounceY = 0; bounceVel = 0;
      }
      innerTarget.value.style.transform = bounceY === 0
        ? ''
        : `translate3d(0, ${(-bounceY).toFixed(2)}px, 0)`;
    }

    rafId = requestAnimationFrame(tick);
  }

  function clampTarget() {
    const el = target.value;
    if (!el) return;
    const maxY = el.scrollHeight - el.clientHeight;
    if (targetY < 0) targetY = 0;
    if (targetY > maxY) targetY = maxY;
  }

  /** 判断 wheel 事件来源是否是 ant 内部"另一个可滚动区"：若是，让原生处理，不拦截 */
  function shouldBypass(e: WheelEvent): boolean {
    /* 修饰键：用户在缩放/横向滚动 */
    if (e.ctrlKey || e.metaKey || e.altKey) return true;
    /* 横向滚动主导 */
    if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) return true;

    let node = e.target as HTMLElement | null;
    while (node && node !== target.value) {
      const style = node instanceof Element ? getComputedStyle(node) : null;
      if (style) {
        const oy = style.overflowY;
        const isScrollable = (oy === 'auto' || oy === 'scroll')
          && node.scrollHeight > node.clientHeight + 1;
        if (isScrollable) {
          /* 内层有可滚动空间则让其原生处理（modal/select/table virtual 等） */
          const atTop = node.scrollTop <= 0;
          const atBottom = node.scrollTop + node.clientHeight >= node.scrollHeight - 1;
          const goingUp = e.deltaY < 0;
          const goingDown = e.deltaY > 0;
          if ((goingUp && !atTop) || (goingDown && !atBottom)) return true;
        }
      }
      node = node.parentElement;
    }
    return false;
  }

  function onWheel(e: WheelEvent) {
    const el = target.value;
    if (!el) return;
    if (shouldBypass(e)) return;

    e.preventDefault();
    userWheeling = true;
    if (wheelEndTimer) window.clearTimeout(wheelEndTimer);
    wheelEndTimer = window.setTimeout(() => { userWheeling = false; }, 160);

    const maxY = el.scrollHeight - el.clientHeight;
    const next = targetY + e.deltaY * cfg.wheelMultiplier;

    if (next < 0 || next > maxY) {
      /* 超出边界：把超出量喂给回弹弹簧 */
      const overshoot = next < 0 ? next : (next - maxY);
      /* 用 atan 把无限大输入压缩到 [-bounceMax, bounceMax] */
      const k = cfg.bounceMax / (Math.PI / 2);
      const compressed = Math.atan(overshoot / cfg.bounceMax) * k;
      bounceY = compressed;
      bounceVel = 0;
      targetY = next < 0 ? 0 : maxY;
    } else {
      targetY = next;
    }
    if (!running) start();
  }

  /** 当原生滚动（键盘 PageDown / 拖拽滚动条 / focus 滚动等）发生时，把目标值同步过去 */
  function onScroll() {
    if (userWheeling) return;
    const el = target.value;
    if (!el) return;
    targetY = el.scrollTop;
    currentY = el.scrollTop;
  }

  function onResize() {
    clampTarget();
  }

  function start() {
    if (running) return;
    running = true;
    lastTs = 0;
    rafId = requestAnimationFrame(tick);
  }
  function stop() {
    running = false;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = 0;
  }

  function bind() {
    const el = target.value;
    if (!el) return;
    /* 同步初始位置 */
    currentY = el.scrollTop;
    targetY = el.scrollTop;
    el.addEventListener('wheel', onWheel, { passive: false });
    el.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onResize);
    start();
  }
  function unbind() {
    const el = target.value;
    stop();
    if (el) {
      el.removeEventListener('wheel', onWheel as EventListener);
      el.removeEventListener('scroll', onScroll as EventListener);
    }
    window.removeEventListener('resize', onResize);
    if (innerTarget?.value) innerTarget.value.style.transform = '';
  }

  onMounted(() => {
    if (!cfg.enabled) return;
    if (isTouchDevice()) return;        /* 触屏设备：保留原生 */
    if (prefersReducedMotion()) return; /* 用户偏好：保留原生 */
    bind();
  });
  onBeforeUnmount(() => unbind());

  /** 编程式滚动到指定位置（带平滑） */
  function scrollTo(y: number) {
    targetY = y;
    clampTarget();
    if (!running) start();
  }
  function scrollBy(dy: number) {
    targetY += dy;
    clampTarget();
    if (!running) start();
  }

  return { scrollTo, scrollBy };
}
