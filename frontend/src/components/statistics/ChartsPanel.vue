<template>
  <div>
    <Chart v-if="chartOptions" ref="chartRef" :options="chartOptions" height="500px" />
    <a-empty v-else description="点击左侧按钮生成图表" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Chart from '@/components/Chart.vue'

defineProps<{ chartOptions: any | null }>()

const chartRef = ref<any>(null)

defineExpose({
  getChartDataUrl: (type: 'png' | 'svg', transparent = false, pixelRatio = 2) =>
    chartRef.value?.getChartDataUrl?.(type, transparent, pixelRatio) || '',
})
</script>
