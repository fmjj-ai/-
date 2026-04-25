<template>
  <div>
    <a-divider orientation="left">热力图配置</a-divider>
    <a-form-item label="选择列（留空则自动使用数值列）">
      <a-select v-model:value="form.columns" mode="multiple" placeholder="选择列">
        <a-select-option v-for="column in numericColumns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item label="相关系数方法">
      <a-select v-model:value="form.method">
        <a-select-option value="pearson">Pearson</a-select-option>
        <a-select-option value="spearman">Spearman</a-select-option>
        <a-select-option value="kendall">Kendall</a-select-option>
      </a-select>
    </a-form-item>
    <a-button type="primary" block :loading="loading" @click="$emit('run')">计算热力图</a-button>
  </div>
</template>

<script setup lang="ts">
export interface CorrelationFormState {
  columns: string[]
  method: 'pearson' | 'spearman' | 'kendall'
}

defineProps<{
  form: CorrelationFormState
  numericColumns: string[]
  loading: boolean
}>()

defineEmits<{ (event: 'run'): void }>()
</script>
