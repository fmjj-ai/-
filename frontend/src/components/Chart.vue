<template>
  <div class="chart-container" ref="chartRef" :style="{ width: width, height: height }"></div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, shallowRef, markRaw } from 'vue';
import * as echarts from 'echarts';
import 'echarts-gl';

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

const chartRef = ref<HTMLElement | null>(null);
const chartInstance = shallowRef<echarts.ECharts | null>(null);

// 初始化图表
const initChart = () => {
  if (chartRef.value) {
    chartInstance.value = markRaw(echarts.init(chartRef.value, props.theme));
    chartInstance.value.setOption(props.options);
    
    // 导出时支持 SVG/PNG，因为初始化默认是 canvas
  }
};

// 监听窗口缩放
const handleResize = () => {
  if (chartInstance.value) {
    chartInstance.value.resize();
  }
};

onMounted(() => {
  initChart();
  window.addEventListener('resize', handleResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
  if (chartInstance.value) {
    chartInstance.value.dispose();
    chartInstance.value = null;
  }
});

// 监听 options 变化
watch(() => props.options, (newOptions) => {
  if (chartInstance.value) {
    chartInstance.value.setOption(newOptions, true);
  }
}, { deep: true });

// 监听 theme 变化
watch(() => props.theme, (newTheme) => {
  if (chartInstance.value) {
    chartInstance.value.dispose();
    initChart();
  }
});

// 导出方法
const exportChart = (type: 'png' | 'svg', transparent = false, pixelRatio = 2) => {
  if (!chartInstance.value) return;
  
  const url = chartInstance.value.getDataURL({
    type,
    pixelRatio,
    backgroundColor: transparent ? 'transparent' : (props.theme === 'dark' ? '#333' : '#fff')
  });
  
  const link = document.createElement('a');
  link.download = `chart-${Date.now()}.${type}`;
  link.href = url;
  link.click();
};

defineExpose({
  exportChart,
  getInstance: () => chartInstance.value
});
</script>

<style scoped>
.chart-container {
  overflow: hidden;
}
</style>
