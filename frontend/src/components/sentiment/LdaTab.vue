<template>
  <template v-if="rows.length">
    <a-space class="mb-16">
      <a-tag color="blue">主题数 {{ latestLdaResult?.n_topics || 0 }}</a-tag>
      <a-tag color="purple">困惑度 {{ formatMetric(latestLdaResult?.perplexity) }}</a-tag>
      <a-button v-if="ldaVisArtifact" type="link" @click="$emit('open-artifact', ldaVisArtifact.id)">
        打开 LDA 可视化
      </a-button>
    </a-space>
    <a-table :columns="columns" :data-source="rows" :pagination="false" size="small" row-key="key" />
  </template>
  <a-empty v-else description="暂无 LDA 结果" />
</template>

<script setup lang="ts">
import { formatMetric } from '@/utils/chartOptions'

defineProps<{
  rows: any[]
  latestLdaResult: any | null
  ldaVisArtifact: any | null
}>()

defineEmits<{ (event: 'open-artifact', artifactId: number): void }>()

const columns = [
  { title: '主题', dataIndex: 'topic', key: 'topic', width: 100 },
  { title: '关键词序号', dataIndex: 'rank', key: 'rank', width: 120 },
  { title: '关键词', dataIndex: 'keyword', key: 'keyword' },
]
</script>

<style scoped>
.mb-16 {
  margin-bottom: 16px;
}
</style>
