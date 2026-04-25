<template>
  <div>
    <a-form-item label="操作类型">
      <a-select v-model:value="form.type">
        <a-select-option value="compute_column">新增计算列</a-select-option>
        <a-select-option value="normalize">标准化 / 归一化</a-select-option>
      </a-select>
    </a-form-item>

    <template v-if="form.type === 'compute_column'">
      <a-form-item label="新列名">
        <a-input v-model:value="form.new_column" />
      </a-form-item>
      <a-form-item label="表达式">
        <a-input v-model:value="form.expression" placeholder="例如：colA + colB" />
      </a-form-item>
    </template>

    <template v-else>
      <a-form-item label="目标列">
        <a-select v-model:value="form.columns" mode="multiple">
          <a-select-option v-for="column in numericColumns" :key="column" :value="column">
            {{ column }}
          </a-select-option>
        </a-select>
      </a-form-item>
      <a-form-item label="标准化方法">
        <a-select v-model:value="form.method">
          <a-select-option value="minmax">Min-Max 归一化</a-select-option>
          <a-select-option value="zscore">Z-Score 标准化</a-select-option>
        </a-select>
      </a-form-item>
    </template>

    <a-button type="primary" block :loading="processing" @click="$emit('apply')">应用变换</a-button>
  </div>
</template>

<script setup lang="ts">
export interface TransformFormState {
  type: 'compute_column' | 'normalize'
  new_column: string
  expression: string
  columns: string[]
  method: 'minmax' | 'zscore'
}

defineProps<{
  form: TransformFormState
  numericColumns: string[]
  processing: boolean
}>()

defineEmits<{ (event: 'apply'): void }>()
</script>
