<template>
  <div>
    <a-divider orientation="left">图表配置</a-divider>
    <a-form-item label="图表类型">
      <a-select v-model:value="form.type">
        <a-select-option value="bar">柱状图</a-select-option>
        <a-select-option value="line">折线图</a-select-option>
        <a-select-option value="pie">饼图</a-select-option>
        <a-select-option value="bar3D">3D 柱状图</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item label="X 轴 / 分组列">
      <a-select v-model:value="form.x" placeholder="选择 X 轴">
        <a-select-option v-for="column in columns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item label="Y 轴 / 指标列">
      <a-select v-model:value="form.y" allow-clear placeholder="计数类图表可留空">
        <a-select-option v-for="column in numericColumns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>
    <a-row :gutter="12">
      <a-col :span="12">
        <a-form-item label="聚合方式">
          <a-select v-model:value="form.agg">
            <a-select-option value="count">计数</a-select-option>
            <a-select-option value="sum">求和</a-select-option>
            <a-select-option value="mean">均值</a-select-option>
          </a-select>
        </a-form-item>
      </a-col>
      <a-col :span="12">
        <a-form-item label="主色">
          <input v-model="form.color" type="color" class="color-input" />
        </a-form-item>
      </a-col>
    </a-row>
    <a-button type="primary" block :loading="loading" @click="$emit('run')">生成图表</a-button>
  </div>
</template>

<script setup lang="ts">
import type { GenericChartType } from '@/utils/chartOptions'

export interface ChartsFormState {
  type: GenericChartType
  x: string
  y: string | undefined
  agg: 'count' | 'sum' | 'mean'
  color: string
}

defineProps<{
  form: ChartsFormState
  columns: string[]
  numericColumns: string[]
  loading: boolean
}>()

defineEmits<{ (event: 'run'): void }>()
</script>

<style scoped>
.color-input {
  width: 100%;
  height: 36px;
  border: 1px solid var(--line-soft);
  border-radius: 10px;
  background: transparent;
  cursor: pointer;
}
</style>
