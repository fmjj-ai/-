<template>
  <a-card v-if="preview" size="small" title="最近一次编码方案">
    <a-descriptions bordered :column="2" size="small">
      <a-descriptions-item label="目标列">{{ preview.column }}</a-descriptions-item>
      <a-descriptions-item label="识别类型">
        {{ preview.value_mode === 'multi_value' ? '多值列' : '单值列' }}
      </a-descriptions-item>
      <a-descriptions-item label="推荐方案">{{ preview.recommended_encoding }}</a-descriptions-item>
      <a-descriptions-item label="唯一值数">{{ preview.unique_count }}</a-descriptions-item>
    </a-descriptions>
    <a-table
      class="mt-16"
      :columns="columns"
      :data-source="rows"
      :pagination="false"
      size="small"
      row-key="value"
    />
  </a-card>
  <a-empty v-else description="先在左侧打开编码预览弹窗" />
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ preview: any | null }>()

const columns = [
  { title: '值', dataIndex: 'value', key: 'value' },
  { title: '出现次数', dataIndex: 'count', key: 'count', width: 120 },
]

const rows = computed(() => {
  const topValues = props.preview?.top_values || []
  return topValues.map((item: any) => ({ value: item.value, count: item.count }))
})
</script>

<style scoped>
.mt-16 {
  margin-top: 16px;
}
</style>
