<template>
  <a-table
    v-if="rows.length"
    :columns="columns"
    :data-source="rows"
    :pagination="false"
    size="small"
    row-key="word"
  />
  <a-empty v-else description="暂无 TF-IDF 结果" />
</template>

<script setup lang="ts">
import { formatMetric } from '@/utils/chartOptions'

defineProps<{ rows: any[] }>()

const columns = [
  { title: '关键词', dataIndex: 'word', key: 'word' },
  {
    title: '得分',
    dataIndex: 'score',
    key: 'score',
    customRender: ({ text }: any) => formatMetric(text),
  },
]
</script>
