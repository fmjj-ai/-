<template>
  <div class="statistics-container">
    <a-row :gutter="24" class="full-height">
      <a-col :span="7" class="full-height">
        <a-card title="数据统计分析" :bordered="false" class="neumorphism-card full-height panel-scroll">
          <a-form layout="vertical">
            <a-form-item label="选择数据集">
              <a-select v-model:value="selectedDatasetId" placeholder="请选择数据集" @change="handleDatasetChange">
                <a-select-option v-for="dataset in datasets" :key="dataset.id" :value="dataset.id">
                  {{ dataset.name }}
                </a-select-option>
              </a-select>
            </a-form-item>

            <a-menu v-if="selectedDatasetId" v-model:selectedKeys="selectedMenu" mode="inline" class="menu-panel">
              <a-menu-item key="overview">自动数据概览</a-menu-item>
              <a-menu-item key="descriptive">描述性统计</a-menu-item>
              <a-menu-item key="correlation">相关性热力图</a-menu-item>
              <a-menu-item key="regression">回归分析</a-menu-item>
              <a-menu-item key="charts">图表展示</a-menu-item>
            </a-menu>

            <template v-if="selectedDatasetId && selectedMenu[0] === 'descriptive'">
              <a-divider orientation="left">统计模式</a-divider>
              <a-form-item>
                <a-radio-group v-model:value="descriptiveMode">
                  <a-radio-button value="summary">轻量摘要</a-radio-button>
                  <a-radio-button value="full">完整统计</a-radio-button>
                </a-radio-group>
              </a-form-item>
              <a-form-item v-if="descriptiveMode === 'summary'" label="列数上限">
                <a-input-number v-model:value="descriptiveLimitColumns" :min="3" :max="20" style="width: 100%" />
              </a-form-item>
              <a-button type="primary" block @click="fetchDescriptive" :loading="loading">刷新描述性统计</a-button>

              <a-divider orientation="left">可视化预览</a-divider>
              <a-form-item label="目标列">
                <a-select v-model:value="descriptiveViz.column" placeholder="选择用于可视化的列">
                  <a-select-option v-for="column in columns" :key="column" :value="column">
                    {{ column }}
                  </a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="图形类型">
                <a-select v-model:value="descriptiveViz.type">
                  <a-select-option v-for="option in descriptiveChartOptions" :key="option.value" :value="option.value">
                    {{ option.label }}
                  </a-select-option>
                </a-select>
              </a-form-item>
              <a-row :gutter="12">
                <a-col :span="12">
                  <a-form-item label="主色">
                    <input v-model="descriptiveViz.color" type="color" class="color-input" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="点形状">
                    <a-select v-model:value="descriptiveViz.shape">
                      <a-select-option value="circle">圆形</a-select-option>
                      <a-select-option value="rect">方形</a-select-option>
                      <a-select-option value="triangle">三角</a-select-option>
                      <a-select-option value="diamond">菱形</a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
              </a-row>
              <a-row v-if="descriptiveViz.type === 'wordfreq'" :gutter="12">
                <a-col :span="12">
                  <a-form-item label="词数上限">
                    <a-input-number v-model:value="descriptiveViz.topN" :min="10" :max="100" style="width: 100%" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="最短词长">
                    <a-input-number v-model:value="descriptiveViz.minLength" :min="1" :max="6" style="width: 100%" />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-row v-if="descriptiveViz.type === 'histogram'" :gutter="12">
                <a-col :span="24">
                  <a-form-item label="分箱数">
                    <a-input-number v-model:value="descriptiveViz.bins" :min="5" :max="60" style="width: 100%" />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-button block @click="generateDescriptiveChart" :loading="loading">生成预览图</a-button>
            </template>

            <template v-if="selectedDatasetId && selectedMenu[0] === 'correlation'">
              <a-divider orientation="left">热力图配置</a-divider>
              <a-form-item label="选择列（留空则自动使用数值列）">
                <a-select v-model:value="corrCols" mode="multiple" placeholder="选择列">
                  <a-select-option v-for="column in numericColumns" :key="column" :value="column">
                    {{ column }}
                  </a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="相关系数方法">
                <a-select v-model:value="corrMethod">
                  <a-select-option value="pearson">Pearson</a-select-option>
                  <a-select-option value="spearman">Spearman</a-select-option>
                  <a-select-option value="kendall">Kendall</a-select-option>
                </a-select>
              </a-form-item>
              <a-button type="primary" block @click="fetchCorrelation" :loading="loading">计算热力图</a-button>
            </template>

            <template v-if="selectedDatasetId && selectedMenu[0] === 'regression'">
              <a-divider orientation="left">回归分析配置</a-divider>
              <a-form-item label="因变量">
                <a-select v-model:value="regY" placeholder="选择 Y 列">
                  <a-select-option v-for="column in numericColumns" :key="column" :value="column">
                    {{ column }}
                  </a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="自变量">
                <a-select v-model:value="regX" mode="multiple" placeholder="选择 X 列">
                  <a-select-option v-for="column in numericColumns" :key="column" :value="column">
                    {{ column }}
                  </a-select-option>
                </a-select>
              </a-form-item>
              <a-row :gutter="12">
                <a-col :span="12">
                  <a-form-item label="回归类型">
                    <a-select v-model:value="regType">
                      <a-select-option value="linear">线性回归</a-select-option>
                      <a-select-option value="polynomial">多项式回归</a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
                <a-col :span="12" v-if="regType === 'polynomial'">
                  <a-form-item label="多项式阶数">
                    <a-input-number v-model:value="polyDegree" :min="2" :max="5" style="width: 100%" />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-button type="primary" block @click="fetchRegression" :loading="loading">运行回归</a-button>
            </template>

            <template v-if="selectedDatasetId && selectedMenu[0] === 'charts'">
              <a-divider orientation="left">图表配置</a-divider>
              <a-form-item label="图表类型">
                <a-select v-model:value="chartType">
                  <a-select-option value="bar">柱状图</a-select-option>
                  <a-select-option value="line">折线图</a-select-option>
                  <a-select-option value="pie">饼图</a-select-option>
                  <a-select-option value="bar3D">3D 柱状图</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="X 轴 / 分组列">
                <a-select v-model:value="chartX" placeholder="选择 X 轴">
                  <a-select-option v-for="column in columns" :key="column" :value="column">
                    {{ column }}
                  </a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="Y 轴 / 指标列">
                <a-select v-model:value="chartY" allow-clear placeholder="计数类图表可留空">
                  <a-select-option v-for="column in numericColumns" :key="column" :value="column">
                    {{ column }}
                  </a-select-option>
                </a-select>
              </a-form-item>
              <a-row :gutter="12">
                <a-col :span="12">
                  <a-form-item label="聚合方式">
                    <a-select v-model:value="chartAgg">
                      <a-select-option value="count">计数</a-select-option>
                      <a-select-option value="sum">求和</a-select-option>
                      <a-select-option value="mean">均值</a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item label="主色">
                    <input v-model="chartColor" type="color" class="color-input" />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-button type="primary" block @click="fetchChartData" :loading="loading">生成图表</a-button>
            </template>
          </a-form>
        </a-card>
      </a-col>

      <a-col :span="17" class="full-height">
        <a-card :title="contentTitle" :bordered="false" class="neumorphism-card full-height panel-scroll">
          <template #extra>
            <a-space v-if="selectedDatasetId">
              <a-button @click="exportReport('markdown')" :loading="reportLoading">导出 Markdown 报告</a-button>
              <a-button @click="exportReport('pdf')" :loading="reportLoading">导出 PDF 报告</a-button>
              <a-button v-if="chartOptions" type="link" @click="exportChartArtifact('png')">导出 PNG</a-button>
              <a-button v-if="chartOptions" type="link" @click="exportChartArtifact('svg')">导出 SVG</a-button>
            </a-space>
          </template>

          <div v-if="!selectedDatasetId" class="empty-state">
            <a-empty description="请先在左侧选择数据集" />
          </div>

          <div v-else-if="loading" class="empty-state">
            <a-skeleton active :paragraph="{ rows: 10 }" />
          </div>

          <div v-else>
            <div v-if="selectedMenu[0] === 'overview' && overviewData">
              <a-descriptions bordered :column="3">
                <a-descriptions-item label="总行数">{{ overviewData.row_count }}</a-descriptions-item>
                <a-descriptions-item label="总列数">{{ overviewData.col_count }}</a-descriptions-item>
                <a-descriptions-item label="文件体积">{{ overviewData.memory_usage_mb }} MB</a-descriptions-item>
              </a-descriptions>
              <a-table
                class="mt-16"
                :columns="overviewColumns"
                :data-source="overviewData.columns"
                :pagination="{ pageSize: 10 }"
                size="small"
                row-key="name"
              />
            </div>

            <div v-if="selectedMenu[0] === 'descriptive'">
              <a-alert v-if="descriptiveSummaryText" type="info" show-icon class="mb-16" :message="descriptiveSummaryText" />
              <a-table
                v-if="formattedDescData.length"
                :columns="descNumericColumns"
                :data-source="formattedDescData"
                :pagination="false"
                size="small"
                row-key="col"
              />

              <a-row v-if="Object.keys(descCategoricalData).length" :gutter="16" class="mt-16">
                <a-col v-for="(stats, column) in descCategoricalData" :key="column" :span="8" class="mb-16">
                  <a-card :title="String(column)" size="small">
                    <p>唯一值数：{{ stats.unique_count ?? '-' }}</p>
                    <p>高频值：</p>
                    <ul v-if="Object.keys(stats.top_values || {}).length">
                      <li v-for="(count, label) in stats.top_values" :key="label">{{ label }}：{{ count }}</li>
                    </ul>
                    <a-empty v-else :image="false" description="当前模式下没有返回高频值" />
                  </a-card>
                </a-col>
              </a-row>

              <div v-if="chartOptions" class="mt-16">
                <Chart ref="chartRef" :options="chartOptions" height="460px" />
              </div>
            </div>

            <div v-if="selectedMenu[0] === 'correlation'">
              <Chart
                v-if="chartOptions"
                ref="chartRef"
                :options="chartOptions"
                :height="heatmapChartHeight"
              />
              <a-empty v-else description="点击左侧按钮计算热力图" />
            </div>

            <div v-if="selectedMenu[0] === 'regression'">
              <Chart v-if="chartOptions" ref="chartRef" :options="chartOptions" height="460px" />
              <a-empty v-else description="点击左侧按钮运行回归分析" />
              <a-descriptions v-if="regData" bordered :column="3" class="mt-16" title="回归指标">
                <a-descriptions-item label="R²">{{ formatMetric(regData.metrics?.r2) }}</a-descriptions-item>
                <a-descriptions-item label="MAE">{{ formatMetric(regData.metrics?.mae) }}</a-descriptions-item>
                <a-descriptions-item label="MSE">{{ formatMetric(regData.metrics?.mse) }}</a-descriptions-item>
              </a-descriptions>
            </div>

            <div v-if="selectedMenu[0] === 'charts'">
              <Chart v-if="chartOptions" ref="chartRef" :options="chartOptions" height="500px" />
              <a-empty v-else description="点击左侧按钮生成图表" />
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'

import Chart from '@/components/Chart.vue'
import request from '@/utils/request'

const route = useRoute()
const projectId = computed(() => String(route.params.projectId || ''))

const datasets = ref<any[]>([])
const selectedDatasetId = ref<number | null>(null)
const currentDataset = ref<any | null>(null)
const columns = ref<string[]>([])
const selectedMenu = ref(['overview'])
const loading = ref(false)
const reportLoading = ref(false)

const overviewData = ref<any | null>(null)
const descData = ref<any | null>(null)
const regData = ref<any | null>(null)
const chartOptions = ref<any | null>(null)
const chartRef = ref<any>(null)

const descriptiveMode = ref<'summary' | 'full'>('summary')
const descriptiveLimitColumns = ref(10)
const descriptiveViz = ref({
  column: '',
  type: 'histogram',
  color: '#1677ff',
  shape: 'circle',
  bins: 20,
  topN: 30,
  minLength: 2
})

const corrCols = ref<string[]>([])
const corrMethod = ref('pearson')
const heatmapColumns = ref<string[]>([])

const regY = ref('')
const regX = ref<string[]>([])
const regType = ref('linear')
const polyDegree = ref(2)

const chartType = ref('bar')
const chartX = ref('')
const chartY = ref<string | undefined>(undefined)
const chartAgg = ref('count')
const chartColor = ref('#4f7cff')

const overviewColumns = [
  { title: '列名', dataIndex: 'name', key: 'name' },
  { title: '类型', dataIndex: 'type', key: 'type' },
  { title: '缺失数', dataIndex: 'missing_count', key: 'missing_count' },
  {
    title: '缺失率',
    dataIndex: 'missing_rate',
    key: 'missing_rate',
    customRender: ({ text }: any) => `${((Number(text) || 0) * 100).toFixed(2)}%`
  },
  { title: '唯一值数', dataIndex: 'unique_count', key: 'unique_count' }
]

const descNumericColumns = [
  { title: '列名', dataIndex: 'col', key: 'col' },
  { title: 'count', dataIndex: 'count', key: 'count' },
  { title: 'mean', dataIndex: 'mean', key: 'mean' },
  { title: 'std', dataIndex: 'std', key: 'std' },
  { title: 'min', dataIndex: 'min', key: 'min' },
  { title: '25%', dataIndex: '25%', key: '25%' },
  { title: '50%', dataIndex: '50%', key: '50%' },
  { title: '75%', dataIndex: '75%', key: '75%' },
  { title: 'max', dataIndex: 'max', key: 'max' }
]

const numericColumns = computed(() => {
  const schema = currentDataset.value?.schema_info || []
  return schema
    .filter((item: any) => {
      const type = String(item.type || '').toLowerCase()
      return ['int', 'float', 'double', 'decimal', 'long', 'short'].some((keyword) => type.includes(keyword))
    })
    .map((item: any) => item.name)
})

const contentTitle = computed(() => {
  const mapping: Record<string, string> = {
    overview: '自动数据概览',
    descriptive: '描述性统计与可视化',
    correlation: '相关性热力图',
    regression: '回归分析',
    charts: '图表展示'
  }
  return mapping[selectedMenu.value[0]] || '数据统计'
})

const heatmapChartHeight = computed(() => {
  const count = heatmapColumns.value.length
  return `${Math.min(Math.max(520, count * 22), 960)}px`
})

const formattedDescData = computed(() => {
  const numeric = descData.value?.numeric || {}
  return Object.keys(numeric).map((column) => ({
    col: column,
    ...Object.fromEntries(
      Object.entries(numeric[column]).map(([key, value]) => [key, formatMetric(value)])
    )
  }))
})

const descCategoricalData = computed(() => descData.value?.categorical || {})

const descriptiveSummaryText = computed(() => {
  const meta = descData.value?.meta
  if (!meta) return ''
  return `${meta.mode === 'summary' ? '轻量摘要' : '完整统计'}，当前统计 ${meta.column_count || 0} 列`
})

const descriptiveChartOptions = computed(() => {
  if (!descriptiveViz.value.column) {
    return [{ value: 'histogram', label: '直方图' }]
  }
  return numericColumns.value.includes(descriptiveViz.value.column)
    ? [
        { value: 'histogram', label: '直方图' },
        { value: 'boxplot', label: '箱线图' }
      ]
    : [
        { value: 'wordfreq', label: '词频图' }
      ]
})

const fetchDatasets = async () => {
  try {
    const res: any = await request.get(`/datasets/project/${projectId.value}`)
    if (res.success) {
      datasets.value = res.data.filter((item: any) => item.status === 'ready')
    }
  } catch {
    message.error('获取数据集失败')
  }
}

const handleDatasetChange = async () => {
  currentDataset.value = datasets.value.find((item) => item.id === selectedDatasetId.value) || null
  columns.value = currentDataset.value?.schema_info?.map((item: any) => item.name) || []
  descriptiveViz.value.column = columns.value[0] || ''
  regY.value = ''
  regX.value = []
  chartX.value = ''
  chartY.value = undefined
  chartOptions.value = null
  overviewData.value = null
  descData.value = null
  regData.value = null
  await fetchCurrentMenuData()
}

watch(
  () => selectedMenu.value[0],
  async () => {
    chartOptions.value = null
    if (selectedDatasetId.value) {
      await fetchCurrentMenuData()
    }
  }
)

watch(
  () => descriptiveViz.value.column,
  () => {
    const allowed = descriptiveChartOptions.value.map((item) => item.value)
    if (!allowed.includes(descriptiveViz.value.type)) {
      descriptiveViz.value.type = allowed[0]
    }
  }
)

const fetchCurrentMenuData = async () => {
  if (selectedMenu.value[0] === 'overview') {
    await fetchOverview()
  } else if (selectedMenu.value[0] === 'descriptive') {
    await fetchDescriptive()
  }
}

const fetchOverview = async () => {
  if (!selectedDatasetId.value) return
  loading.value = true
  try {
    const res: any = await request.get(`/statistics/${selectedDatasetId.value}/overview`)
    if (res.success) {
      overviewData.value = res.data
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '获取概览失败')
  } finally {
    loading.value = false
  }
}

const fetchDescriptive = async () => {
  if (!selectedDatasetId.value) return
  loading.value = true
  try {
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/descriptive`, {
      mode: descriptiveMode.value,
      limit_columns: descriptiveMode.value === 'summary' ? descriptiveLimitColumns.value : null,
      columns: descriptiveMode.value === 'summary' ? columns.value.slice(0, descriptiveLimitColumns.value) : null
    })
    if (res.success) {
      descData.value = res.data
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '获取描述性统计失败')
  } finally {
    loading.value = false
  }
}

const buildHistogramOptions = (labels: string[], counts: number[], color: string) => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: labels, axisLabel: { rotate: 30 } },
  yAxis: { type: 'value' },
  series: [
    {
      type: 'bar',
      data: counts,
      itemStyle: { color, borderRadius: [8, 8, 0, 0] }
    }
  ]
})

const buildBoxplotOptions = (column: string, box: number[], outliers: number[], color: string, shape: string) => ({
  tooltip: { trigger: 'item' },
  xAxis: { type: 'category', data: [column] },
  yAxis: { type: 'value' },
  series: [
    {
      name: '箱线图',
      type: 'boxplot',
      data: [box],
      itemStyle: { color, borderColor: color }
    },
    {
      name: '异常值',
      type: 'scatter',
      symbol: shape,
      itemStyle: { color },
      data: outliers.map((value) => [0, value])
    }
  ]
})

const buildWordFreqOptions = (rows: Array<{ label: string; value: number }>, color: string) => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: rows.map((item) => item.label), axisLabel: { rotate: 28 } },
  yAxis: { type: 'value' },
  series: [
    {
      type: 'bar',
      data: rows.map((item) => item.value),
      itemStyle: { color, borderRadius: [8, 8, 0, 0] }
    }
  ]
})

const truncateLabel = (value: string, maxLength: number) => (
  value.length > maxLength ? `${value.slice(0, maxLength)}…` : value
)

const calcZoomEnd = (total: number, visibleCount: number) => {
  if (total <= visibleCount) {
    return 100
  }

  return Math.max(20, Number(((visibleCount / total) * 100).toFixed(2)))
}

const resizeChartSoon = () => {
  nextTick(() => {
    requestAnimationFrame(() => {
      chartRef.value?.getInstance?.()?.resize()
    })
  })
}

const buildCorrelationHeatmapOptions = (payload: any) => {
  const columnCount = payload.columns.length
  const showCellLabel = columnCount <= 18

  return {
    animation: false,
    tooltip: {
      confine: true,
      position: 'top',
      formatter: ({ data: item }: any) => {
        const xLabel = payload.columns[item[0]] ?? ''
        const yLabel = payload.columns[item[1]] ?? ''
        const value = item[2]
        return `${yLabel}<br/>${xLabel}<br/>相关系数：${value === null ? '-' : Number(value).toFixed(4)}`
      }
    },
    grid: {
      left: 240,
      right: 96,
      top: 24,
      bottom: 150
    },
    xAxis: {
      type: 'category',
      data: payload.columns,
      splitArea: { show: true },
      axisLabel: {
        interval: 0,
        rotate: columnCount > 10 ? 40 : 20,
        formatter: (value: string) => truncateLabel(String(value), 12)
      }
    },
    yAxis: {
      type: 'category',
      data: payload.columns,
      splitArea: { show: true },
      axisLabel: {
        interval: 0,
        formatter: (value: string) => truncateLabel(String(value), 16)
      }
    },
    dataZoom: [
      {
        type: 'slider',
        xAxisIndex: 0,
        filterMode: 'none',
        bottom: 72,
        height: 14,
        start: 0,
        end: calcZoomEnd(columnCount, 10)
      },
      {
        type: 'inside',
        xAxisIndex: 0,
        filterMode: 'none'
      },
      {
        type: 'slider',
        yAxisIndex: 0,
        filterMode: 'none',
        right: 20,
        width: 14,
        top: 24,
        bottom: 150,
        start: 0,
        end: calcZoomEnd(columnCount, 12)
      },
      {
        type: 'inside',
        yAxisIndex: 0,
        filterMode: 'none'
      }
    ],
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: 'vertical',
      right: 18,
      top: 'middle'
    },
    series: [
      {
        name: 'Correlation',
        type: 'heatmap',
        data: payload.data,
        progressive: 0,
        label: {
          show: showCellLabel,
          formatter: ({ data: item }: any) => (item[2] === null ? '-' : Number(item[2]).toFixed(2))
        },
        emphasis: {
          itemStyle: {
            borderColor: '#ffffff',
            borderWidth: 1
          }
        }
      }
    ]
  }
}

const generateDescriptiveChart = async () => {
  if (!selectedDatasetId.value || !descriptiveViz.value.column) {
    message.warning('请选择用于可视化的目标列')
    return
  }
  loading.value = true
  try {
    if (descriptiveViz.value.type === 'histogram') {
      const res: any = await request.post(`/chart-calculations/${selectedDatasetId.value}/histogram`, {
        column: descriptiveViz.value.column,
        bins: descriptiveViz.value.bins
      })
      if (res.success) {
        chartOptions.value = buildHistogramOptions(res.data.labels, res.data.counts, descriptiveViz.value.color)
      }
    } else if (descriptiveViz.value.type === 'boxplot') {
      const res: any = await request.post(`/chart-calculations/${selectedDatasetId.value}/boxplot`, {
        column: descriptiveViz.value.column
      })
      if (res.success) {
        chartOptions.value = buildBoxplotOptions(
          descriptiveViz.value.column,
          res.data.box,
          res.data.outliers,
          descriptiveViz.value.color,
          descriptiveViz.value.shape
        )
      }
    } else {
      const res: any = await request.post(`/chart-calculations/${selectedDatasetId.value}/wordcloud`, {
        text_column: descriptiveViz.value.column,
        top_n: descriptiveViz.value.topN,
        min_length: descriptiveViz.value.minLength
      })
      if (res.success) {
        const rows = (res.data.words || []).map((item: any) => ({ label: item.name, value: item.value }))
        chartOptions.value = buildWordFreqOptions(rows, descriptiveViz.value.color)
      }
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '生成描述性可视化失败')
  } finally {
    loading.value = false
  }
}

const fetchCorrelation = async () => {
  if (!selectedDatasetId.value) return
  loading.value = true
  chartOptions.value = null
  heatmapColumns.value = []
  try {
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/correlation`, {
      columns: corrCols.value.length > 0 ? corrCols.value : null,
      method: corrMethod.value
    })
    if (res.success) {
      const data = res.data
      heatmapColumns.value = data.columns || []
      chartOptions.value = buildCorrelationHeatmapOptions(data)
      resizeChartSoon()
    }
  } catch (error: any) {
    chartOptions.value = null
    heatmapColumns.value = []
    message.error(error.response?.data?.detail || '计算热力图失败')
  } finally {
    loading.value = false
  }
}

const fetchRegression = async () => {
  if (!selectedDatasetId.value || !regY.value || regX.value.length === 0) {
    message.warning('请选择因变量和自变量')
    return
  }
  loading.value = true
  try {
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/regression`, {
      y_col: regY.value,
      x_cols: regX.value,
      reg_type: regType.value,
      poly_degree: polyDegree.value
    })
    if (res.success) {
      regData.value = res.data
      if (regX.value.length === 1 && res.data.fit_line) {
        chartOptions.value = {
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'value', name: regX.value[0] },
          yAxis: { type: 'value', name: regY.value },
          series: [
            {
              name: '拟合线',
              type: 'line',
              showSymbol: false,
              data: res.data.fit_line,
              lineStyle: { width: 3, color: chartColor.value }
            }
          ]
        }
      } else {
        chartOptions.value = null
      }
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '回归分析失败')
  } finally {
    loading.value = false
  }
}

const fetchChartData = async () => {
  if (!selectedDatasetId.value || !chartX.value) {
    message.warning('请选择 X 轴 / 分组列')
    return
  }
  loading.value = true
  try {
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/aggregation`, {
      x_col: chartX.value,
      y_col: chartY.value || null,
      agg_method: chartAgg.value,
      max_bins: 50
    })
    if (res.success) {
      const data = res.data
      if (chartType.value === 'pie') {
        chartOptions.value = {
          tooltip: { trigger: 'item' },
          legend: { orient: 'vertical', left: 'left' },
          series: [
            {
              type: 'pie',
              radius: '58%',
              data: data.x_axis.map((item: string, index: number) => ({ name: item, value: data.y_axis[index] }))
            }
          ]
        }
      } else if (chartType.value === 'bar3D') {
        chartOptions.value = {
          tooltip: {},
          visualMap: {
            max: Math.max(...data.y_axis, 1),
            inRange: { color: ['#e6f4ff', '#91caff', chartColor.value] }
          },
          xAxis3D: { type: 'category', data: data.x_axis },
          yAxis3D: { type: 'category', data: ['Series'] },
          zAxis3D: { type: 'value' },
          grid3D: { boxWidth: 180, boxDepth: 20, viewControl: { alpha: 12, beta: 18 } },
          series: [
            {
              type: 'bar3D',
              data: data.y_axis.map((value: number, index: number) => [index, 0, value]),
              shading: 'lambert'
            }
          ]
        }
      } else {
        chartOptions.value = {
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: data.x_axis },
          yAxis: { type: 'value' },
          series: [
            {
              type: chartType.value,
              smooth: chartType.value === 'line',
              data: data.y_axis,
              itemStyle: { color: chartColor.value },
              lineStyle: { color: chartColor.value }
            }
          ]
        }
      }
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '生成图表失败')
  } finally {
    loading.value = false
  }
}

const dataUrlToFile = async (dataUrl: string, filename: string) => {
  const response = await fetch(dataUrl)
  const blob = await response.blob()
  return new File([blob], filename, { type: blob.type || 'application/octet-stream' })
}

const buildChartExportName = (type: 'png' | 'svg') => {
  const datasetName = currentDataset.value?.name || '数据集'
  const actionNameMap: Record<string, string> = {
    descriptive: '描述性分析图',
    correlation: '相关性热力图',
    regression: '回归分析图',
    charts: '统计图表'
  }
  return `${datasetName}${actionNameMap[selectedMenu.value[0]] || '图表'}.${type}`
}

const exportChartArtifact = async (type: 'png' | 'svg') => {
  const dataUrl = chartRef.value?.getChartDataUrl?.(type, false, 2)
  if (!dataUrl) {
    message.warning('当前没有可导出的图表')
    return
  }
  try {
    const file = await dataUrlToFile(dataUrl, buildChartExportName(type))
    const formData = new FormData()
    formData.append('project_id', projectId.value)
    formData.append('name', buildChartExportName(type))
    formData.append('file', file)
    const res: any = await request.post('/artifacts/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    if (res.success) {
      message.success(`图表已导出到导出中心：${res.data.name}`)
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '图表导出失败')
  }
}

const buildReportBlocks = async () => {
  const blocks: any[] = []
  if (overviewData.value) {
    blocks.push({ type: 'text', content: `数据集总行数：${overviewData.value.row_count}，总列数：${overviewData.value.col_count}` })
  }
  if (descData.value?.numeric) {
    const firstNumericColumn = Object.keys(descData.value.numeric)[0]
    if (firstNumericColumn) {
      blocks.push({
        type: 'table',
        title: `${firstNumericColumn} 描述性统计`,
        data: descData.value.numeric[firstNumericColumn]
      })
    }
  }
  if (chartOptions.value) {
    const dataUrl = chartRef.value?.getChartDataUrl?.('png', false, 2)
    if (dataUrl) {
      blocks.push({
        type: 'chart',
        title: contentTitle.value,
        image_url: dataUrl
      })
    }
  }
  if (!blocks.length) {
    blocks.push({ type: 'text', content: '当前页面暂无可写入报告的结果，请先生成统计结果或图表。' })
  }
  return blocks
}

const exportReport = async (reportType: 'markdown' | 'pdf') => {
  if (!selectedDatasetId.value) return
  reportLoading.value = true
  try {
    if (!overviewData.value) {
      await fetchOverview()
    }
    if (!descData.value) {
      await fetchDescriptive()
    }
    const blocks = await buildReportBlocks()
    const datasetName = currentDataset.value?.name || '数据集'
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/report`, {
      report_type: reportType,
      title: `${datasetName}统计分析报告`,
      content_blocks: blocks
    })
    if (res.success) {
      message.success(`报告已生成并进入导出中心：${res.data.name}`)
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '报告生成失败')
  } finally {
    reportLoading.value = false
  }
}

const formatMetric = (value: any) => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(4) : '-'
}

onMounted(() => {
  fetchDatasets()
})
</script>

<style scoped>
.statistics-container {
  padding: 24px;
  height: calc(100vh - 64px);
}

.full-height {
  height: 100%;
}

.panel-scroll {
  overflow-y: auto;
}

.neumorphism-card {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-outer);
  background: var(--bg-elevated);
}

.menu-panel {
  background: transparent;
  border-right: none;
  margin-top: 8px;
}

.empty-state {
  min-height: 420px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.color-input {
  width: 100%;
  height: 36px;
  border: 1px solid var(--line-soft);
  border-radius: 10px;
  background: transparent;
  cursor: pointer;
}

.mt-16 {
  margin-top: 16px;
}

.mb-16 {
  margin-bottom: 16px;
}
</style>
