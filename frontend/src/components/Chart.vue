<template>
  <div class="chart-wrapper" ref="wrapperRef" :style="{ width: width, height: height }">
    <a-skeleton active :loading="!isVisible || !options" :paragraph="{ rows: 8 }">
      <div class="chart-container" ref="chartRef" style="width: 100%; height: 100%;"></div>
    </a-skeleton>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, shallowRef, markRaw } from 'vue';
import * as echarts from 'echarts';
import 'echarts-gl';
import { useIntersectionObserver } from '@vueuse/core';

const props = defineProps({
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '400px'
  },
  options: {
    type: Object,
    required: true
  },
  theme: {
    type: String,
    default: 'default' // 'default', 'dark', 'macarons', etc.
  }
});

const wrapperRef = ref<HTMLElement | null>(null);
const chartRef = ref<HTMLElement | null>(null);
const chartInstance = shallowRef<echarts.ECharts | null>(null);
const isVisible = ref(false);

// 初始化图表
const initChart = () => {
  if (chartRef.value && isVisible.value && props.options) {
    if (!chartInstance.value) {
      chartInstance.value = markRaw(echarts.init(chartRef.value, props.theme));
    }
    chartInstance.value.setOption(props.options);
  }
};

const handleResize = () => {
  if (chartInstance.value) {
    chartInstance.value.resize();
  }
};

useIntersectionObserver(
  wrapperRef,
  ([{ isIntersecting }]) => {
    if (isIntersecting) {
      isVisible.value = true;
      initChart();
    }
  },
  { rootMargin: '100px' }
);

onMounted(() => {
  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  if (chartInstance.value) {
    chartInstance.value.dispose();
    chartInstance.value = null;
  }
});

watch(() => props.options, (newOptions) => {
  if (chartInstance.value && isVisible.value) {
    chartInstance.value.setOption(newOptions, true);
  } else if (isVisible.value) {
    initChart();
  }
}, { deep: true });

watch(() => props.theme, () => {
  if (chartInstance.value) {
    chartInstance.value.dispose();
    chartInstance.value = null;
    initChart();
  }
});

// 导出方法
const getChartDataUrl = (type: 'png' | 'svg', transparent = false, pixelRatio = 2) => {
  if (!chartInstance.value) return '';

  return chartInstance.value.getDataURL({
    type,
    pixelRatio,
    backgroundColor: transparent ? 'transparent' : (props.theme === 'dark' ? '#333' : '#fff')
  });
};

const exportChart = (type: 'png' | 'svg', transparent = false, pixelRatio = 2) => {
  const url = getChartDataUrl(type, transparent, pixelRatio);
  if (!url) return '';

  const link = document.createElement('a');
  link.download = `chart-${Date.now()}.${type}`;
  link.href = url;
  link.click();
  return url;
};

defineExpose({
  exportChart,
  getChartDataUrl,
  getInstance: () => chartInstance.value
});
</script>

<style scoped>
.chart-wrapper {
  overflow: hidden;
  position: relative;
}
.chart-container {
  overflow: hidden;
}
</style>
