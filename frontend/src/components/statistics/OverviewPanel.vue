<template>
  <div v-if="data">
    <a-descriptions bordered :column="3">
      <a-descriptions-item label="总行数">{{ data.row_count }}</a-descriptions-item>
      <a-descriptions-item label="总列数">{{ data.col_count }}</a-descriptions-item>
      <a-descriptions-item label="文件体积">{{ data.memory_usage_mb }} MB</a-descriptions-item>
    </a-descriptions>
    <a-table
      class="mt-16"
      :columns="overviewColumns"
      :data-source="data.columns"
      :pagination="{ pageSize: 10 }"
      size="small"
      row-key="name"
    />
  </div>
  <a-empty v-else description="暂无概览数据" />
</template>

<script setup lang="ts">
defineProps<{ data: any | null }>()

const overviewColumns = [
  { title: '列名', dataIndex: 'name', key: 'name' },
  { title: '类型', dataIndex: 'type', key: 'type' },
  { title: '缺失数', dataIndex: 'missing_count', key: 'missing_count' },
  {
    title: '缺失率',
    dataIndex: 'missing_rate',
    key: 'missing_rate',
    customRender: ({ text }: any) => `${((Number(text) || 0) * 100).toFixed(2)}%`,
  },
  { title: '唯一值数', dataIndex: 'unique_count', key: 'unique_count' },
]
</script>

<style scoped>
.mt-16 {
  margin-top: 16px;
}
</style>
