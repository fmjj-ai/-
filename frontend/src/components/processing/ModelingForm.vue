<template>
  <div>
    <a-form-item label="任务类型">
      <a-select v-model:value="form.task_type">
        <a-select-option value="classification">分类</a-select-option>
        <a-select-option value="regression">回归</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item label="模型算法">
      <a-select v-model:value="form.algorithm">
        <a-select-option value="rf">RandomForest</a-select-option>
        <a-select-option value="xgb">XGBoost</a-select-option>
        <a-select-option value="lgbm">LightGBM</a-select-option>
        <a-select-option value="mlp">MLP</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item label="目标列">
      <a-select v-model:value="form.target_col" placeholder="选择目标列">
        <a-select-option v-for="column in columns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item label="特征列">
      <a-select v-model:value="form.feature_cols" mode="multiple" placeholder="留空则自动使用其余数值列">
        <a-select-option v-for="column in numericColumns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item label="测试集比例">
      <a-slider
        v-model:value="form.test_size"
        :min="0.1"
        :max="0.5"
        :step="0.05"
        :tip-formatter="formatPercent"
      />
    </a-form-item>
    <a-button type="primary" block :loading="processing" @click="$emit('run')">训练并评估</a-button>
  </div>
</template>

<script setup lang="ts">
export interface ModelingFormState {
  task_type: 'classification' | 'regression'
  algorithm: 'rf' | 'xgb' | 'lgbm' | 'mlp'
  target_col: string
  feature_cols: string[]
  test_size: number
}

defineProps<{
  form: ModelingFormState
  columns: string[]
  numericColumns: string[]
  processing: boolean
}>()

defineEmits<{ (event: 'run'): void }>()

const formatPercent = (value: number) => `${Math.round(value * 100)}%`
</script>
