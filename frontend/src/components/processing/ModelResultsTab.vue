<template>
  <a-space direction="vertical" style="width: 100%">
    <a-card v-for="task in tasks" :key="task.id" :title="task.name" size="small">
      <a-descriptions bordered :column="3" size="small">
        <a-descriptions-item label="状态">{{ task.status }}</a-descriptions-item>
        <a-descriptions-item label="任务类型">{{ task.result?.kind }}</a-descriptions-item>
        <a-descriptions-item label="完成时间">
          {{ formatDateTime(task.finished_at || task.created_at) }}
        </a-descriptions-item>
      </a-descriptions>

      <a-table
        class="mt-16"
        :columns="metricColumns"
        :data-source="buildMetricRows(task)"
        :pagination="false"
        size="small"
        row-key="metric"
      />

      <a-table
        v-if="task.result?.feature_importance?.length"
        class="mt-16"
        :columns="featureImportanceColumns"
        :data-source="task.result.feature_importance"
        :pagination="false"
        size="small"
        row-key="feature"
      />
    </a-card>
    <a-empty v-if="!tasks.length" description="暂无聚类或建模结果" />
  </a-space>
</template>

<script setup lang="ts">
import dayjs from 'dayjs'
import { formatMetric } from '@/utils/chartOptions'

defineProps<{ tasks: any[] }>()

const metricColumns = [
  { title: '指标', dataIndex: 'metric', key: 'metric' },
  { title: '结果', dataIndex: 'value', key: 'value' },
]

const featureImportanceColumns = [
  { title: '特征', dataIndex: 'feature', key: 'feature' },
  {
    title: '重要性',
    dataIndex: 'importance',
    key: 'importance',
    customRender: ({ text }: any) => formatMetric(text),
  },
]

const buildMetricRows = (task: any) => {
  const metrics = task.result?.metrics || {}
  return Object.keys(metrics).map((key) => ({
    metric: key,
    value: formatMetric(metrics[key]),
  }))
}

const formatDateTime = (value: string) => (value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-')
</script>

<style scoped>
.mt-16 {
  margin-top: 16px;
}
</style>
