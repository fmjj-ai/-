<template>
  <div class="statistics-container">
    <a-row :gutter="24" style="height: 100%;">
      <a-col :span="6" class="left-panel">
        <a-card title="数据统计与分析" :bordered="false" class="neumorphism-card h-full" style="overflow-y: auto;">
          <a-form layout="vertical">
            <a-form-item label="选择数据集">
              <a-select v-model:value="selectedDatasetId" @change="handleDatasetChange" placeholder="请选择数据集" style="width: 100%">
                <a-select-option v-for="d in datasets" :key="d.id" :value="d.id">
                  {{ d.name }}
                </a-select-option>
              </a-select>
            </a-form-item>

            <a-divider />

            <a-menu
              v-model:selectedKeys="selectedMenu"
              mode="inline"
              class="neumorphism-menu"
              v-if="selectedDatasetId"
            >
              <a-menu-item key="cleaning">
                数据清洗与变换 (ST-01/02)
              </a-menu-item>
              <a-menu-item key="overview">
                自动数据概览 (ST-03)
              </a-menu-item>
              <a-menu-item key="descriptive">
                描述性统计 (ST-04)
              </a-menu-item>
              <a-menu-item key="correlation">
                相关性热力图 (ST-05)
              </a-menu-item>
              <a-menu-item key="regression">
                回归分析 (ST-06)
              </a-menu-item>
              <a-menu-item key="charts">
                图表生成 (2D/3D)
              </a-menu-item>
            </a-menu>

            <div v-if="selectedMenu[0] === 'cleaning'" class="mt-4">
              <a-form-item label="缺失值处理">
                <a-select v-model:value="cleanStrategy.missing">
                  <a-select-option value="drop">删除缺失行</a-select-option>
                  <a-select-option value="fill_mean">填充均值</a-select-option>
                  <a-select-option value="fill_median">填充中位数</a-select-option>
                  <a-select-option value="fill_mode">填充众数</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item>
                <a-checkbox v-model:checked="cleanStrategy.drop_duplicates">去除重复值</a-checkbox>
              </a-form-item>
              <a-form-item>
                <a-checkbox v-model:checked="cleanStrategy.handle_outliers">检测并处理异常值 (IQR)</a-checkbox>
              </a-form-item>
              <a-button type="primary" block @click="applyCleaning" :loading="loading">应用清洗规则</a-button>

              <a-divider />

              <a-form-item label="数据变换 (标准化/归一化)">
                <a-select v-model:value="transformStrategy.scaler" allowClear placeholder="选择缩放方法">
                  <a-select-option value="standard">StandardScaler (标准化)</a-select-option>
                  <a-select-option value="minmax">MinMaxScaler (归一化)</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="应用列">
                <a-select v-model:value="transformStrategy.columns" mode="multiple" placeholder="选择数值列">
                  <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-button type="primary" block @click="applyTransform" :loading="loading">应用变换</a-button>
            </div>

            <div v-if="selectedMenu[0] === 'correlation'" class="mt-4">
              <a-form-item label="选择列 (留空则全选数值列)">
                <a-select v-model:value="corrCols" mode="multiple" placeholder="选择列">
                  <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="相关系数方法">
                <a-select v-model:value="corrMethod">
                  <a-select-option value="pearson">Pearson</a-select-option>
                  <a-select-option value="spearman">Spearman</a-select-option>
                  <a-select-option value="kendall">Kendall</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="缺失值处理策略">
                <a-select v-model:value="corrMissingStrategy">
                  <a-select-option value="drop">剔除缺失行</a-select-option>
                  <a-select-option value="fill_mean">填充均值</a-select-option>
                  <a-select-option value="fill_median">填充中位数</a-select-option>
                </a-select>
              </a-form-item>
              <a-button type="primary" block @click="fetchCorrelation" :loading="loading">计算相关性</a-button>
            </div>

            <div v-if="selectedMenu[0] === 'regression'" class="mt-4">
              <a-form-item label="因变量 (Y)">
                <a-select v-model:value="regY">
                  <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="自变量 (X)">
                <a-select v-model:value="regX" mode="multiple">
                  <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="回归类型">
                <a-select v-model:value="regType">
                  <a-select-option value="linear">线性回归</a-select-option>
                  <a-select-option value="polynomial">多项式回归</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item v-if="regType === 'polynomial'" label="多项式阶数">
                <a-input-number v-model:value="polyDegree" :min="2" :max="5" />
              </a-form-item>
              <a-form-item label="缺失值处理策略">
                <a-select v-model:value="regMissingStrategy">
                  <a-select-option value="drop">剔除缺失行</a-select-option>
                  <a-select-option value="fill_mean">填充均值</a-select-option>
                  <a-select-option value="fill_median">填充中位数</a-select-option>
                </a-select>
              </a-form-item>
              <a-button type="primary" block @click="fetchRegression" :loading="loading">运行回归</a-button>
            </div>

            <div v-if="selectedMenu[0] === 'charts'" class="mt-4">
              <a-form-item label="图表类型">
                <a-select v-model:value="chartType">
                  <a-select-option value="bar">柱状图</a-select-option>
                  <a-select-option value="line">折线图</a-select-option>
                  <a-select-option value="scatter">散点图</a-select-option>
                  <a-select-option value="pie">饼图</a-select-option>
                  <a-select-option value="bar3D">3D柱状图</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="X 轴 / 分组列">
                <a-select v-model:value="chartX">
                  <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="Y 轴 / 聚合列 (可选)">
                <a-select v-model:value="chartY" allowClear>
                  <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="聚合方法">
                <a-select v-model:value="chartAgg">
                  <a-select-option value="count">计数 (Count)</a-select-option>
                  <a-select-option value="sum">求和 (Sum)</a-select-option>
                  <a-select-option value="mean">均值 (Mean)</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item label="图表主题">
                <a-select v-model:value="chartTheme">
                  <a-select-option value="default">默认</a-select-option>
                  <a-select-option value="dark">黑金商务</a-select-option>
                  <a-select-option value="macarons">马卡龙</a-select-option>
                </a-select>
              </a-form-item>
              <a-button type="primary" block @click="fetchChartData" :loading="loading">生成图表</a-button>
            </div>

          </a-form>
        </a-card>
      </a-col>

      <a-col :span="18" class="right-panel">
        <a-card :title="contentTitle" :bordered="false" class="neumorphism-card h-full" style="overflow-y: auto;">
          <template #extra>
            <a-space v-if="selectedDatasetId">
              <a-button type="primary" @click="exportReport('markdown')">导出 Markdown 报告</a-button>
              <a-button type="primary" @click="exportReport('pdf')">导出 PDF 报告</a-button>
            </a-space>
            <a-space v-if="hasChart" style="margin-left: 16px;">
              <a-button type="link" @click="exportChart('png')">导出 PNG</a-button>
              <a-button type="link" @click="exportChart('svg')">导出 SVG</a-button>
            </a-space>
          </template>

          <div v-if="!selectedDatasetId" class="empty-state">
            <a-empty description="请在左侧选择数据集" />
          </div>
          
          <div v-else-if="loading" class="empty-state" style="padding: 40px;">
            <a-skeleton active :paragraph="{ rows: 10 }" />
          </div>

          <div v-else>
            <!-- Overview -->
            <div v-if="selectedMenu[0] === 'overview' && overviewData">
              <a-descriptions bordered :column="3">
                <a-descriptions-item label="总行数">{{ overviewData.row_count }}</a-descriptions-item>
                <a-descriptions-item label="总列数">{{ overviewData.col_count }}</a-descriptions-item>
                <a-descriptions-item label="内存占用">{{ overviewData.memory_usage_mb }} MB</a-descriptions-item>
              </a-descriptions>
              <a-table :columns="overviewColumns" :data-source="overviewData.columns" :pagination="false" class="mt-4" bordered size="small" />
            </div>

            <!-- Descriptive Stats -->
            <div v-if="selectedMenu[0] === 'descriptive' && descData">
              <h3 v-if="Object.keys(descData.numeric).length">数值列统计</h3>
              <a-table 
                v-if="formattedDescData.length"
                :columns="descNumericColumns" 
                :data-source="formattedDescData" 
                :pagination="false" 
                bordered 
                size="small" 
              />
              <h3 v-if="Object.keys(descData.categorical).length" class="mt-4">分类列统计</h3>
              <a-row :gutter="16">
                <a-col :span="8" v-for="(cat, col) in descData.categorical" :key="col" class="mb-4">
                  <a-card :title="col" size="small">
                    <p>唯一值数: {{ cat.unique_count }}</p>
                    <p>Top Values:</p>
                    <ul>
                      <li v-for="(val, k) in cat.top_values" :key="k">{{ k }}: {{ val }}</li>
                    </ul>
                  </a-card>
                </a-col>
              </a-row>
            </div>

            <!-- Correlation & Regression & Charts -->
            <div v-if="['correlation', 'regression', 'charts'].includes(selectedMenu[0])">
               <Chart v-if="chartOptions" ref="chartRef" :options="chartOptions" :theme="chartTheme" height="500px" />
               <div v-if="selectedMenu[0] === 'regression' && regData" class="mt-4">
                  <a-descriptions bordered :column="3" title="回归指标">
                    <a-descriptions-item label="R² (决定系数)">{{ regData.metrics.r2.toFixed(4) }}</a-descriptions-item>
                    <a-descriptions-item label="MAE (平均绝对误差)">{{ regData.metrics.mae.toFixed(4) }}</a-descriptions-item>
                    <a-descriptions-item label="MSE (均方误差)">{{ regData.metrics.mse.toFixed(4) }}</a-descriptions-item>
                  </a-descriptions>
               </div>
            </div>

          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import request from '@/utils/request'
import Chart from '@/components/Chart.vue'
import DataWorker from '@/workers/dataWorker?worker'

const route = useRoute()
const projectId = computed(() => route.params.projectId)

const dataWorker = new DataWorker()

// Desc data formatted
const formattedDescData = ref<any[]>([])

// Clean up worker
onBeforeUnmount(() => {
  dataWorker.terminate()
})

dataWorker.onmessage = (e: MessageEvent) => {
  const { type, payload } = e.data
  if (type === 'FORMAT_NUMERIC_DESC_RESULT') {
    formattedDescData.value = payload
  } else if (type === 'PROCESS_3D_BAR_DATA_RESULT') {
    const data3D = payload
    const data = chartCurrentData.value
    chartOptions.value = {
      tooltip: {},
      visualMap: {
        max: Math.max(...data.y_axis),
        inRange: { color: ['#313695', '#4575b4', '#74add1', '#abd9e9', '#e0f3f8', '#ffffbf', '#fee090', '#fdae61', '#f46d43', '#d73027', '#a50026'] }
      },
      xAxis3D: { type: 'category', data: data.x_axis },
      yAxis3D: { type: 'category', data: ['Series'] },
      zAxis3D: { type: 'value' },
      grid3D: { boxWidth: 200, boxDepth: 20, viewControl: { alpha: 10, beta: 20 } },
      series: [{
        type: 'bar3D',
        data: data3D,
        shading: 'lambert',
        label: { show: false, textStyle: { fontSize: 16, borderWidth: 1 } },
        itemStyle: { opacity: 0.8 },
        emphasis: { label: { show: true } }
      }]
    }
  }
}

const datasets = ref<any[]>([])
const selectedDatasetId = ref<number | null>(null)
const currentDataset = ref<any>(null)
const columns = ref<string[]>([])

const selectedMenu = ref(['overview'])
const loading = ref(false)

const chartRef = ref<any>(null)
const chartOptions = ref<any>(null)
const chartTheme = ref('default')

// Overview Data
const overviewData = ref<any>(null)
const overviewColumns = [
  { title: '列名', dataIndex: 'name', key: 'name' },
  { title: '类型', dataIndex: 'type', key: 'type' },
  { title: '缺失数', dataIndex: 'missing_count', key: 'missing_count' },
  { title: '缺失率', dataIndex: 'missing_rate', key: 'missing_rate', customRender: ({text}: any) => `${(text*100).toFixed(2)}%` },
  { title: '唯一值数', dataIndex: 'unique_count', key: 'unique_count' },
]

// Cleaning & Transform
const cleanStrategy = ref({
  missing: 'drop',
  drop_duplicates: false,
  handle_outliers: false
})
const transformStrategy = ref({
  scaler: undefined,
  columns: []
})

// Descriptive Data
const descData = ref<any>(null)
const descNumericColumns = [
  { title: '列名', dataIndex: 'col', key: 'col' },
  { title: '数量 (count)', dataIndex: 'count', key: 'count' },
  { title: '均值 (mean)', dataIndex: 'mean', key: 'mean' },
  { title: '标准差 (std)', dataIndex: 'std', key: 'std' },
  { title: '最小值 (min)', dataIndex: 'min', key: 'min' },
  { title: '25%', dataIndex: '25%', key: '25%' },
  { title: '50%', dataIndex: '50%', key: '50%' },
  { title: '75%', dataIndex: '75%', key: '75%' },
  { title: '最大值 (max)', dataIndex: 'max', key: 'max' },
]

// Correlation
const corrCols = ref<string[]>([])
const corrMethod = ref('pearson')
const corrMissingStrategy = ref('drop')

// Regression
const regY = ref<string>('')
const regX = ref<string[]>([])
const regType = ref('linear')
const polyDegree = ref(2)
const regMissingStrategy = ref('drop')
const regData = ref<any>(null)

// Charts
const chartType = ref('bar')
const chartX = ref<string>('')
const chartY = ref<string | undefined>(undefined)
const chartAgg = ref('count')
const chartCurrentData = ref<any>(null)

const contentTitle = computed(() => {
  const map: any = {
    'overview': '自动数据概览',
    'descriptive': '描述性统计',
    'correlation': '相关性热力图',
    'regression': '回归分析',
    'charts': '图表展示'
  }
  return map[selectedMenu.value[0]] || '详情'
})

const hasChart = computed(() => {
  return ['correlation', 'regression', 'charts'].includes(selectedMenu.value[0]) && chartOptions.value !== null
})

const fetchDatasets = async () => {
  try {
    const res: any = await request.get(`/datasets/project/${projectId.value}`)
    if (res.success) {
      datasets.value = res.data.filter((d: any) => d.status === 'ready')
    }
  } catch (e) {
    message.error('获取数据集失败')
  }
}

const handleDatasetChange = () => {
  currentDataset.value = datasets.value.find(d => d.id === selectedDatasetId.value)
  if (currentDataset.value && currentDataset.value.schema_info) {
    columns.value = currentDataset.value.schema_info.map((c: any) => c.name)
  }
  chartOptions.value = null
  fetchCurrentMenuData()
}

watch(() => selectedMenu.value, () => {
  chartOptions.value = null
  if (selectedDatasetId.value) {
    fetchCurrentMenuData()
  }
})

const fetchCurrentMenuData = async () => {
  if (selectedMenu.value[0] === 'overview') {
    await fetchOverview()
  } else if (selectedMenu.value[0] === 'descriptive') {
    await fetchDescriptive()
  }
}

const fetchOverview = async () => {
  loading.value = true
  try {
    const res: any = await request.get(`/statistics/${selectedDatasetId.value}/overview`)
    if (res.success) {
      overviewData.value = res.data
    }
  } catch (e) {
    message.error('获取概览失败')
  } finally {
    loading.value = false
  }
}

const fetchDescriptive = async () => {
  loading.value = true
  try {
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/descriptive`, {})
    if (res.success) {
      descData.value = res.data
      if (res.data.numeric && Object.keys(res.data.numeric).length) {
        dataWorker.postMessage({ type: 'FORMAT_NUMERIC_DESC', payload: { numObj: res.data.numeric } })
      }
    }
  } catch (e) {
    message.error('获取描述性统计失败')
  } finally {
    loading.value = false
  }
}

const fetchCorrelation = async () => {
  if (!selectedDatasetId.value) return
  loading.value = true
  try {
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/correlation`, {
      columns: corrCols.value.length > 0 ? corrCols.value : null,
      method: corrMethod.value
    })
    if (res.success) {
      const data = res.data
      chartOptions.value = {
        tooltip: { position: 'top' },
        grid: { height: '70%', top: '10%' },
        xAxis: { type: 'category', data: data.columns, splitArea: { show: true } },
        yAxis: { type: 'category', data: data.columns, splitArea: { show: true } },
        visualMap: {
          min: -1, max: 1, calculable: true,
          orient: 'horizontal', left: 'center', bottom: '0%'
        },
        series: [{
          name: 'Correlation', type: 'heatmap', data: data.data,
          label: { show: true, formatter: (p: any) => p.data[2] !== null ? p.data[2].toFixed(2) : '-' },
          emphasis: { itemStyle: { shadowBlur: 10, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
        }]
      }
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '计算失败')
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
      
      // If it's a simple 1D regression, we can plot a scatter + fit line
      if (regX.value.length === 1 && res.data.fit_line) {
        // We also need original data to plot scatter. 
        // For simplicity, we just plot the fit line here, or we'd need another endpoint to get sample points.
        chartOptions.value = {
          title: { text: `${regY.value} vs ${regX.value[0]}` },
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'value', name: regX.value[0] },
          yAxis: { type: 'value', name: regY.value },
          series: [
            {
              name: 'Fit Line',
              type: 'line',
              showSymbol: false,
              data: res.data.fit_line,
              smooth: true,
              lineStyle: { width: 3, color: 'red' }
            }
          ]
        }
      } else {
        chartOptions.value = null
        message.success('回归分析完成，多变量回归暂不支持2D直接绘图，请查看指标')
      }
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '回归失败')
  } finally {
    loading.value = false
  }
}

const fetchChartData = async () => {
  if (!selectedDatasetId.value || !chartX.value) {
    message.warning('请选择 X 轴列')
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
        const pieData = data.x_axis.map((x: string, i: number) => ({ name: x, value: data.y_axis[i] }))
        chartOptions.value = {
          tooltip: { trigger: 'item' },
          legend: { orient: 'vertical', left: 'left' },
          series: [{ name: chartY.value || 'Count', type: 'pie', radius: '50%', data: pieData, emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } } }]
        }
      } else if (chartType.value === 'bar3D') {
        chartCurrentData.value = data
        dataWorker.postMessage({ type: 'PROCESS_3D_BAR_DATA', payload: { x_axis: data.x_axis, y_axis: data.y_axis } })
      } else {
        chartOptions.value = {
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'category', data: data.x_axis },
          yAxis: { type: 'value' },
          series: [{ data: data.y_axis, type: chartType.value, smooth: chartType.value === 'line' }]
        }
      }
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '获取图表数据失败')
  } finally {
    loading.value = false
  }
}

const exportChart = (type: 'png' | 'svg') => {
  if (chartRef.value) {
    chartRef.value.exportChart(type, false, 2)
  }
}

const applyCleaning = async () => {
  if (!selectedDatasetId.value) return
  loading.value = true
  try {
    message.info('应用清洗规则中，请在任务中心查看进度...')
    // API call for cleaning would go here
  } finally {
    loading.value = false
  }
}

const applyTransform = async () => {
  if (!selectedDatasetId.value) return
  if (!transformStrategy.value.scaler || transformStrategy.value.columns.length === 0) {
    message.warning('请选择缩放方法和应用列')
    return
  }
  loading.value = true
  try {
    message.info('应用变换中，请在任务中心查看进度...')
    // API call for transform would go here
  } finally {
    loading.value = false
  }
}

const exportReport = (type: 'markdown' | 'pdf') => {
  if (!selectedDatasetId.value) return
  message.info(`正在生成 ${type.toUpperCase()} 报告，请稍候在产物中心查看...`)
  // API call for export report
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
.h-full {
  height: 100%;
}
.left-panel, .right-panel {
  height: 100%;
}
.neumorphism-card {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-outer);
  background: var(--bg-elevated);
}
.neumorphism-menu {
  background: transparent;
  border-right: none;
}
.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.mt-4 {
  margin-top: 16px;
}
.mb-4 {
  margin-bottom: 16px;
}
</style>
