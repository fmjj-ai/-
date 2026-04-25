<template>
  <div v-if="missingStats || outlierPreview">
    <a-row :gutter="16" class="mb-16">
      <a-col :span="6">
        <a-card size="small" title="异常值数量">
          {{ outlierPreview?.outlier_count ?? '-' }}
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small" title="下界">
          {{ formatMetric(outlierPreview?.summary?.lower_bound) }}
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small" title="上界">
          {{ formatMetric(outlierPreview?.summary?.upper_bound) }}
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small" title="均值 / 标准差">
          {{ formatMetric(outlierPreview?.summary?.mean) }} / {{ formatMetric(outlierPreview?.summary?.std) }}
        </a-card>
      </a-col>
    </a-row>

    <a-row :gutter="16">
      <a-col :span="10">
        <Chart v-if="outlierChartOptions" :options="outlierChartOptions" height="360px" />
        <a-empty v-else description="先执行异常值预览" />
      </a-col>
      <a-col :span="14">
        <a-card size="small" title="异常值样例">
          <a-table
            :columns="outlierSampleColumns"
            :data-source="outlierSampleRows"
            :pagination="false"
            size="small"
            row-key="key"
          />
        </a-card>
        <a-card size="small" title="缺失值统计" class="mt-16">
          <a-table
            v-if="missingStats"
            :columns="missingStatsColumns"
            :data-source="missingStats.columns"
            :pagination="{ pageSize: 6 }"
            size="small"
            row-key="name"
          />
          <a-empty v-else description="先点击左侧按钮加载缺失值统计" />
        </a-card>
      </a-col>
    </a-row>
  </div>
  <a-empty v-else description="先在左侧执行缺失值统计或异常值预览" />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import Chart from '@/components/Chart.vue'
import { formatMetric } from '@/utils/chartOptions'

const props = defineProps<{
  missingStats: any | null
  outlierPreview: any | null
  outlierChartOptions: any | null
}>()

const outlierSampleRows = computed(() => {
  const values = props.outlierPreview?.sample_values || []
  return values.map((value: number, index: number) => ({
    key: index,
    index: index + 1,
    value,
  }))
})

const outlierSampleColumns = [
  { title: '序号', dataIndex: 'index', key: 'index', width: 80 },
  { title: '异常值样例', dataIndex: 'value', key: 'value' },
]

const missingStatsColumns = [
  { title: '列名', dataIndex: 'name', key: 'name' },
  { title: '缺失数', dataIndex: 'missing_count', key: 'missing_count' },
  { title: '总数', dataIndex: 'total_count', key: 'total_count' },
  {
    title: '缺失率',
    dataIndex: 'missing_rate',
    key: 'missing_rate',
    customRender: ({ text }: any) => `${((Number(text) || 0) * 100).toFixed(2)}%`,
  },
]
</script>

<style scoped>
.mt-16 {
  margin-top: 16px;
}
.mb-16 {
  margin-bottom: 16px;
}
</style>
