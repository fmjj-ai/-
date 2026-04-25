<template>
  <a-space direction="vertical" style="width: 100%">
    <a-button block :loading="processing" @click="$emit('load-missing-stats')">查看缺失值统计</a-button>
    <a-form-item label="异常值目标列" style="margin-bottom: 0">
      <a-select v-model:value="form.column" placeholder="选择数值列">
        <a-select-option v-for="column in numericColumns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>
    <a-row :gutter="12">
      <a-col :span="12">
        <a-form-item label="检测方法" style="margin-bottom: 0">
          <a-select v-model:value="form.method">
            <a-select-option value="iqr">IQR</a-select-option>
            <a-select-option value="zscore">Z-Score</a-select-option>
          </a-select>
        </a-form-item>
      </a-col>
      <a-col :span="12" v-if="form.method === 'zscore'">
        <a-form-item label="Z 阈值" style="margin-bottom: 0">
          <a-input-number v-model:value="form.z_threshold" :min="0.5" :step="0.5" style="width: 100%" />
        </a-form-item>
      </a-col>
    </a-row>
    <a-form-item label="处理策略" style="margin-bottom: 0">
      <a-select v-model:value="form.strategy">
        <a-select-option value="clip">截断到边界</a-select-option>
        <a-select-option value="remove">删除异常行</a-select-option>
        <a-select-option value="replace_mean">替换为均值</a-select-option>
      </a-select>
    </a-form-item>
    <div class="split-action-row">
      <a-button block :loading="processing" @click="$emit('preview-outliers')">异常值预览</a-button>
      <a-button type="primary" block :loading="processing" @click="$emit('apply-outliers')">异常值处理</a-button>
    </div>
  </a-space>
</template>

<script setup lang="ts">
export interface CleaningFormState {
  column: string
  method: 'iqr' | 'zscore'
  strategy: 'clip' | 'remove' | 'replace_mean'
  z_threshold: number
}

defineProps<{
  form: CleaningFormState
  numericColumns: string[]
  processing: boolean
}>()

defineEmits<{
  (event: 'load-missing-stats'): void
  (event: 'preview-outliers'): void
  (event: 'apply-outliers'): void
}>()
</script>

<style scoped>
.split-action-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  width: 100%;
}
</style>
