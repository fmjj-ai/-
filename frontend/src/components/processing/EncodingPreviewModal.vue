<template>
  <a-modal
    :open="open"
    title="编码预览与确认"
    width="760px"
    :confirm-loading="processing"
    @update:open="(v: boolean) => $emit('update:open', v)"
    @ok="$emit('confirm')"
  >
    <template v-if="preview">
      <a-descriptions bordered :column="2" size="small">
        <a-descriptions-item label="目标列">{{ preview.column }}</a-descriptions-item>
        <a-descriptions-item label="列类型">
          {{ preview.value_mode === 'multi_value' ? '多值列' : '单值列' }}
        </a-descriptions-item>
        <a-descriptions-item label="推荐方式">{{ preview.recommended_encoding }}</a-descriptions-item>
        <a-descriptions-item label="唯一值数">{{ preview.unique_count }}</a-descriptions-item>
      </a-descriptions>

      <a-form layout="vertical" class="mt-16">
        <a-form-item label="编码方式">
          <a-radio-group :value="selectedMode" @update:value="(v: string) => $emit('update:selectedMode', v)">
            <a-radio v-for="option in preview.encoding_options" :key="option.key" :value="option.key">
              {{ option.label }}
            </a-radio>
          </a-radio-group>
        </a-form-item>
      </a-form>

      <a-table
        :columns="previewColumns"
        :data-source="previewRows"
        :pagination="false"
        size="small"
        row-key="value"
      />

      <a-table
        v-if="selectedMode === 'ordinal_encode'"
        class="mt-16"
        :columns="ordinalMappingColumns"
        :data-source="ordinalMappingRows"
        :pagination="false"
        size="small"
        row-key="value"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'encoded'">
            <a-input-number v-model:value="record.encoded" :min="1" style="width: 100%" />
          </template>
        </template>
      </a-table>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  open: boolean
  preview: any | null
  selectedMode: string
  ordinalMappingRows: any[]
  processing: boolean
}>()

defineEmits<{
  (event: 'update:open', value: boolean): void
  (event: 'update:selectedMode', value: string): void
  (event: 'confirm'): void
}>()

const previewColumns = [
  { title: '值', dataIndex: 'value', key: 'value' },
  { title: '出现次数', dataIndex: 'count', key: 'count', width: 120 },
]

const ordinalMappingColumns = [
  { title: '原始值', dataIndex: 'value', key: 'value' },
  { title: '映射值', dataIndex: 'encoded', key: 'encoded', width: 160 },
]

const previewRows = computed(() => {
  const topValues = props.preview?.top_values || []
  return topValues.map((item: any) => ({ value: item.value, count: item.count }))
})
</script>

<style scoped>
.mt-16 {
  margin-top: 16px;
}
</style>
