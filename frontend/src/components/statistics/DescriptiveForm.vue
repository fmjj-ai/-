<template>
  <div>
    <a-divider orientation="left">统计模式</a-divider>
    <a-form-item>
      <a-radio-group v-model:value="form.mode">
        <a-radio-button value="summary">轻量摘要</a-radio-button>
        <a-radio-button value="full">完整统计</a-radio-button>
      </a-radio-group>
    </a-form-item>
    <a-form-item v-if="form.mode === 'summary'" label="列数上限">
      <a-input-number v-model:value="form.limitColumns" :min="3" :max="20" style="width: 100%" />
    </a-form-item>
    <a-button type="primary" block :loading="loading" @click="$emit('refresh')">
      刷新描述性统计
    </a-button>

    <a-divider orientation="left">可视化预览</a-divider>
    <a-form-item label="目标列">
      <a-select v-model:value="form.viz.column" placeholder="选择用于可视化的列">
        <a-select-option v-for="column in columns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item label="图形类型">
      <a-select v-model:value="form.viz.type">
        <a-select-option v-for="option in chartTypeOptions" :key="option.value" :value="option.value">
          {{ option.label }}
        </a-select-option>
      </a-select>
    </a-form-item>
    <a-row :gutter="12">
      <a-col :span="12">
        <a-form-item label="主色">
          <input v-model="form.viz.color" type="color" class="color-input" />
        </a-form-item>
      </a-col>
      <a-col :span="12">
        <a-form-item label="点形状">
          <a-select v-model:value="form.viz.shape">
            <a-select-option value="circle">圆形</a-select-option>
            <a-select-option value="rect">方形</a-select-option>
            <a-select-option value="triangle">三角</a-select-option>
            <a-select-option value="diamond">菱形</a-select-option>
          </a-select>
        </a-form-item>
      </a-col>
    </a-row>
    <a-row v-if="form.viz.type === 'wordfreq'" :gutter="12">
      <a-col :span="12">
        <a-form-item label="词数上限">
          <a-input-number v-model:value="form.viz.topN" :min="10" :max="100" style="width: 100%" />
        </a-form-item>
      </a-col>
      <a-col :span="12">
        <a-form-item label="最短词长">
          <a-input-number v-model:value="form.viz.minLength" :min="1" :max="6" style="width: 100%" />
        </a-form-item>
      </a-col>
    </a-row>
    <a-row v-if="form.viz.type === 'histogram'" :gutter="12">
      <a-col :span="24">
        <a-form-item label="分箱数">
          <a-input-number v-model:value="form.viz.bins" :min="5" :max="60" style="width: 100%" />
        </a-form-item>
      </a-col>
    </a-row>
    <a-button block :loading="loading" @click="$emit('generate-chart')">生成预览图</a-button>
  </div>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'

export interface DescriptiveFormState {
  mode: 'summary' | 'full'
  limitColumns: number
  viz: {
    column: string
    type: string
    color: string
    shape: string
    bins: number
    topN: number
    minLength: number
  }
}

const props = defineProps<{
  form: DescriptiveFormState
  columns: string[]
  numericColumns: string[]
  loading: boolean
}>()

defineEmits<{
  (event: 'refresh'): void
  (event: 'generate-chart'): void
}>()

const chartTypeOptions = computed(() => {
  if (!props.form.viz.column) {
    return [{ value: 'histogram', label: '直方图' }]
  }
  return props.numericColumns.includes(props.form.viz.column)
    ? [
        { value: 'histogram', label: '直方图' },
        { value: 'boxplot', label: '箱线图' },
      ]
    : [{ value: 'wordfreq', label: '词频图' }]
})

watch(
  () => props.form.viz.column,
  () => {
    const allowed = chartTypeOptions.value.map((item) => item.value)
    if (!allowed.includes(props.form.viz.type)) {
      props.form.viz.type = allowed[0]
    }
  }
)
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
