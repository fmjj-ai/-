<template>
  <div>
    <a-divider orientation="left">回归分析配置</a-divider>
    <a-form-item label="因变量">
      <a-select v-model:value="form.y" placeholder="选择 Y 列">
        <a-select-option v-for="column in numericColumns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item label="自变量">
      <a-select v-model:value="form.x" mode="multiple" placeholder="选择 X 列">
        <a-select-option v-for="column in numericColumns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>
    <a-row :gutter="12">
      <a-col :span="12">
        <a-form-item label="回归类型">
          <a-select v-model:value="form.type">
            <a-select-option value="linear">线性回归</a-select-option>
            <a-select-option value="polynomial">多项式回归</a-select-option>
          </a-select>
        </a-form-item>
      </a-col>
      <a-col :span="12" v-if="form.type === 'polynomial'">
        <a-form-item label="多项式阶数">
          <a-input-number v-model:value="form.polyDegree" :min="2" :max="5" style="width: 100%" />
        </a-form-item>
      </a-col>
    </a-row>
    <a-button type="primary" block :loading="loading" @click="$emit('run')">运行回归</a-button>
  </div>
</template>

<script setup lang="ts">
export interface RegressionFormState {
  y: string
  x: string[]
  type: 'linear' | 'polynomial'
  polyDegree: number
}

defineProps<{
  form: RegressionFormState
  numericColumns: string[]
  loading: boolean
}>()

defineEmits<{ (event: 'run'): void }>()
</script>
