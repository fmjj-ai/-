<template>
  <div>
    <Chart v-if="chartOptions" ref="chartRef" :options="chartOptions" :height="chartHeight" />
    <a-empty v-else description="点击左侧按钮计算热力图" />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Chart from '@/components/Chart.vue'

const props = defineProps<{
  chartOptions: any | null
  columns: string[]
}>()

const chartRef = ref<any>(null)

const chartHeight = computed(() => {
  const count = props.columns.length
  return `${Math.min(Math.max(520, count * 22), 960)}px`
})

defineExpose({
  getChartDataUrl: (type: 'png' | 'svg', transparent = false, pixelRatio = 2) =>
    chartRef.value?.getChartDataUrl?.(type, transparent, pixelRatio) || '',
  resize: () => chartRef.value?.getInstance?.()?.resize(),
})
</script>
