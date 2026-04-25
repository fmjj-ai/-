<template>
  <div>
    <Chart v-if="chartOptions" ref="chartRef" :options="chartOptions" height="460px" />
    <a-empty v-else description="点击左侧按钮运行回归分析" />
    <a-descriptions v-if="data" bordered :column="3" class="mt-16" title="回归指标">
      <a-descriptions-item label="R²">{{ formatMetric(data.metrics?.r2) }}</a-descriptions-item>
      <a-descriptions-item label="MAE">{{ formatMetric(data.metrics?.mae) }}</a-descriptions-item>
      <a-descriptions-item label="MSE">{{ formatMetric(data.metrics?.mse) }}</a-descriptions-item>
    </a-descriptions>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import Chart from '@/components/Chart.vue'
import { formatMetric } from '@/utils/chartOptions'

defineProps<{
  data: any | null
  chartOptions: any | null
}>()

const chartRef = ref<any>(null)

defineExpose({
  getChartDataUrl: (type: 'png' | 'svg', transparent = false, pixelRatio = 2) =>
    chartRef.value?.getChartDataUrl?.(type, transparent, pixelRatio) || '',
})
</script>

<style scoped>
.mt-16 {
  margin-top: 16px;
}
</style>
