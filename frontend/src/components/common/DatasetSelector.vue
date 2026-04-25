<template>
  <a-form-item :label="label">
    <a-select
      :value="modelValue"
      :placeholder="placeholder"
      :allow-clear="allowClear"
      :disabled="disabled"
      @change="handleChange"
    >
      <a-select-option v-for="dataset in datasets" :key="dataset.id" :value="dataset.id">
        {{ dataset.name }}
      </a-select-option>
    </a-select>
  </a-form-item>
</template>

<script setup lang="ts">
import type { DatasetItem } from '@/composables/useDatasets'

const props = withDefaults(
  defineProps<{
    modelValue: number | null
    datasets: DatasetItem[]
    label?: string
    placeholder?: string
    allowClear?: boolean
    disabled?: boolean
  }>(),
  {
    label: '选择数据集',
    placeholder: '请选择数据集',
    allowClear: false,
    disabled: false,
  }
)

const emit = defineEmits<{
  (event: 'update:modelValue', value: number | null): void
  (event: 'change', value: number | null): void
}>()

const handleChange = (value: number | null) => {
  emit('update:modelValue', value)
  emit('change', value)
}

// 避免 TS 未使用警告
void props
</script>
