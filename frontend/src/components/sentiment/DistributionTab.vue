<template>
  <div v-if="rows.length" class="chart-shell">
    <Chart :options="chartOptions" height="420px" />
    <a-table
      class="mt-16"
      :columns="columns"
      :data-source="rows"
      :pagination="false"
      size="small"
      row-key="label"
    />
  </div>
  <a-empty v-else description="暂无情感分布结果，请先执行分析" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Chart from '@/components/Chart.vue'

const props = defineProps<{ rows: any[] }>()

const columns = [
  { title: '情感类型', dataIndex: 'label', key: 'label' },
  { title: '数量', dataIndex: 'count', key: 'count' },
  {
    title: '占比',
    dataIndex: 'ratio',
    key: 'ratio',
    customRender: ({ text }: any) => `${((Number(text) || 0) * 100).toFixed(2)}%`,
  },
]

const chartOptions = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: ({ data }: any) =>
      `${data.name}<br/>数量：${data.value}<br/>占比：${((data.ratio || 0) * 100).toFixed(2)}%`,
  },
  legend: { orient: 'vertical', left: 'left' },
  series: [
    {
      name: '情感分布',
      type: 'pie',
      radius: ['40%', '70%'],
      label: {
        formatter: ({ data }: any) =>
          `${data.name}: ${data.value} (${((data.ratio || 0) * 100).toFixed(1)}%)`,
      },
      data: props.rows.map((item: any) => ({
        name: item.label,
        value: item.count,
        ratio: item.ratio,
      })),
    },
  ],
}))
</script>

<style scoped>
.chart-shell {
  min-height: 420px;
}
.mt-16 {
  margin-top: 16px;
}
</style>
