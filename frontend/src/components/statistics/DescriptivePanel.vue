<template>
  <div>
    <a-alert
      v-if="summaryText"
      type="info"
      show-icon
      class="mb-16"
      :message="summaryText"
    />
    <a-table
      v-if="numericRows.length"
      :columns="numericTableColumns"
      :data-source="numericRows"
      :pagination="false"
      size="small"
      row-key="col"
    />

    <a-row v-if="Object.keys(categoricalData).length" :gutter="16" class="mt-16">
      <a-col v-for="(stats, column) in categoricalData" :key="column" :span="8" class="mb-16">
        <a-card :title="String(column)" size="small">
          <p>唯一值数：{{ stats.unique_count ?? '-' }}</p>
          <p>高频值：</p>
          <ul v-if="Object.keys(stats.top_values || {}).length">
            <li v-for="(count, label) in stats.top_values" :key="label">{{ label }}：{{ count }}</li>
          </ul>
          <a-empty v-else :image="false" description="当前模式下没有返回高频值" />
        </a-card>
      </a-col>
    </a-row>

    <div v-if="chartOptions" class="mt-16">
      <Chart ref="chartRef" :options="chartOptions" height="460px" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import Chart from '@/components/Chart.vue'
import { formatMetric } from '@/utils/chartOptions'

const props = defineProps<{
  data: any | null
  chartOptions: any | null
}>()

const chartRef = ref<any>(null)

const summaryText = computed(() => {
  const meta = props.data?.meta
  if (!meta) return ''
  return `${meta.mode === 'summary' ? '轻量摘要' : '完整统计'}，当前统计 ${meta.column_count || 0} 列`
})

const numericRows = computed(() => {
  const numeric = props.data?.numeric || {}
  return Object.keys(numeric).map((column) => ({
    col: column,
    ...Object.fromEntries(
      Object.entries(numeric[column]).map(([key, value]) => [key, formatMetric(value)])
    ),
  }))
})

const categoricalData = computed(() => props.data?.categorical || {})

const numericTableColumns = [
  { title: '列名', dataIndex: 'col', key: 'col' },
  { title: 'count', dataIndex: 'count', key: 'count' },
  { title: 'mean', dataIndex: 'mean', key: 'mean' },
  { title: 'std', dataIndex: 'std', key: 'std' },
  { title: 'min', dataIndex: 'min', key: 'min' },
  { title: '25%', dataIndex: '25%', key: '25%' },
  { title: '50%', dataIndex: '50%', key: '50%' },
  { title: '75%', dataIndex: '75%', key: '75%' },
  { title: 'max', dataIndex: 'max', key: 'max' },
]

defineExpose({
  getChartDataUrl: (type: 'png' | 'svg', transparent = false, pixelRatio = 2) =>
    chartRef.value?.getChartDataUrl?.(type, transparent, pixelRatio) || '',
})
</script>

<style scoped>
.mt-16 {
  margin-top: 16px;
}
.mb-16 {
  margin-bottom: 16px;
}
</style>
