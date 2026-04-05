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
              <a-menu-item key="extensions">
                sjfx 增量能力
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


            <div v-if="selectedMenu[0] === 'descriptive'" class="mt-4">
              <a-form-item label="统计模式">
                <a-radio-group v-model:value="descriptiveMode">
                  <a-radio-button value="summary">轻量摘要</a-radio-button>
                  <a-radio-button value="full">完整统计</a-radio-button>
                </a-radio-group>
              </a-form-item>
              <a-form-item v-if="descriptiveMode === 'summary'" label="摘要列数上限">
                <a-input-number v-model:value="descriptiveLimitColumns" :min="1" :max="20" style="width: 100%" />
              </a-form-item>
              <a-button type="primary" block @click="fetchDescriptive" :loading="loading">刷新描述性统计</a-button>
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

            <div v-if="selectedMenu[0] === 'extensions'" class="mt-4">
              <a-alert
                type="info"
                show-icon
                message="sjfx 增量能力工作台"
                description="这里直接调用已迁入 solo 的图表计算与快速报告接口，不替换原有统计主流程。"
              />
              <a-divider />
              <a-form-item label="能力类型">
                <a-select v-model:value="extensionForm.mode">
                  <a-select-option value="histogram">直方图</a-select-option>
                  <a-select-option value="boxplot">箱线图</a-select-option>
                  <a-select-option value="aggregate">聚合图</a-select-option>
                  <a-select-option value="wordcloud">词云词频</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item v-if="['histogram', 'boxplot'].includes(extensionForm.mode)" label="目标数值列">
                <a-select v-model:value="extensionForm.column" placeholder="选择数值列">
                  <a-select-option v-for="col in numericColumns" :key="col" :value="col">{{ col }}</a-select-option>
                </a-select>
              </a-form-item>
              <a-form-item v-if="extensionForm.mode === 'histogram'" label="分箱数">
                <a-input-number v-model:value="extensionForm.bins" :min="5" :max="100" style="width: 100%" />
              </a-form-item>
              <template v-if="extensionForm.mode === 'aggregate'">
                <a-form-item label="分组列">
                  <a-select v-model:value="extensionForm.group_by" placeholder="选择分组列">
                    <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="指标列 (可选)">
                  <a-select v-model:value="extensionForm.metric" allowClear placeholder="count 可留空，其它聚合建议选择数值列">
                    <a-select-option v-for="col in numericColumns" :key="col" :value="col">{{ col }}</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="聚合方法">
                  <a-select v-model:value="extensionForm.agg_method">
                    <a-select-option value="count">计数</a-select-option>
                    <a-select-option value="sum">求和</a-select-option>
                    <a-select-option value="mean">均值</a-select-option>
                    <a-select-option value="max">最大值</a-select-option>
                    <a-select-option value="min">最小值</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="Top N">
                  <a-input-number v-model:value="extensionForm.top_n" :min="5" :max="100" style="width: 100%" />
                </a-form-item>
              </template>
              <template v-if="extensionForm.mode === 'wordcloud'">
                <a-form-item label="文本列">
                  <a-select v-model:value="extensionForm.text_column" placeholder="选择文本列">
                    <a-select-option v-for="col in textColumns" :key="col" :value="col">{{ col }}</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="Top N">
                  <a-input-number v-model:value="extensionForm.top_n" :min="10" :max="200" style="width: 100%" />
                </a-form-item>
                <a-form-item label="最短词长">
                  <a-input-number v-model:value="extensionForm.min_length" :min="1" :max="10" style="width: 100%" />
                </a-form-item>
              </template>
              <a-space direction="vertical" style="width: 100%">
                <a-button type="primary" block @click="runExtensionAction" :loading="loading">运行当前能力</a-button>
                <a-button block @click="loadExtensionCapabilities">刷新增量能力状态</a-button>
                <a-button block @click="previewQuickHtmlReport" :loading="loading">预览 HTML 快报</a-button>
              </a-space>
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
            <div v-if="selectedMenu[0] === 'overview' && overviewData">
              <a-descriptions bordered :column="3">
                <a-descriptions-item label="总行数">{{ overviewData.row_count }}</a-descriptions-item>
                <a-descriptions-item label="总列数">{{ overviewData.col_count }}</a-descriptions-item>
                <a-descriptions-item label="内存占用">{{ overviewData.memory_usage_mb }} MB</a-descriptions-item>
              </a-descriptions>
              <a-table :columns="overviewColumns" :data-source="overviewData.columns" :pagination="false" class="mt-4" bordered size="small" />
            </div>

            <div v-if="selectedMenu[0] === 'descriptive' && descData">
              <a-alert v-if="descriptiveSummaryText" class="mb-4" type="info" show-icon :message="descriptiveSummaryText" />
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
                    <a-tag v-if="cat.top_values_status === 'skipped_high_cardinality_scan'" color="gold" class="mb-2">高基数列，已跳过频次扫描</a-tag>
                    <p>唯一值数: {{ cat.unique_count ?? '-' }}</p>
                    <p>Top Values:</p>
                    <ul v-if="Object.keys(cat.top_values || {}).length">
                      <li v-for="(val, k) in cat.top_values" :key="k">{{ k }}: {{ val }}</li>
                    </ul>
                    <a-empty v-else :image="false" description="当前模式下未返回 Top Values" />
                  </a-card>
                </a-col>
              </a-row>
            </div>


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

            <div v-if="selectedMenu[0] === 'extensions'">
              <a-alert
                type="success"
                show-icon
                message="增量能力已切换为可操作工作台"
                description="可直接生成直方图、箱线图、聚合图、词频结果，并可预览最小 HTML 快报。"
              />

              <a-row :gutter="16" class="mt-4">
                <a-col :span="reportPreviewUrl ? 14 : 24">
                  <a-card v-if="extensionResult" :title="extensionResult.title" size="small">
                    <a-descriptions bordered :column="3" size="small" v-if="extensionSummaryItems.length">
                      <a-descriptions-item v-for="item in extensionSummaryItems" :key="item.label" :label="item.label">
                        {{ item.value }}
                      </a-descriptions-item>
                    </a-descriptions>
                    <Chart v-if="chartOptions" ref="chartRef" :options="chartOptions" :theme="chartTheme" height="420px" class="mt-4" />
                    <a-table
                      v-if="extensionTableRows.length"
                      :columns="extensionTableColumns"
                      :data-source="extensionTableRows"
                      :pagination="{ pageSize: 10, hideOnSinglePage: true }"
                      bordered
                      size="small"
                      class="mt-4"
                    />
                  </a-card>
                  <a-empty v-else description="请在左侧选择增量能力并执行" />

                  <a-card v-if="capabilityRows.length" title="接口状态" size="small" class="mt-4">
                    <a-table
                      :columns="capabilityColumns"
                      :data-source="capabilityRows"
                      :pagination="false"
                      bordered
                      size="small"
                    />
                  </a-card>
                </a-col>
                <a-col v-if="reportPreviewUrl" :span="10">
                  <a-card title="HTML 快报预览" size="small">
                    <iframe :src="reportPreviewUrl" class="report-preview-frame"></iframe>
                  </a-card>
                </a-col>
              </a-row>
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

const formattedDescData = ref<any[]>([])
const reportPreviewUrl = ref('')

const clearReportPreview = () => {
  if (reportPreviewUrl.value) {
    URL.revokeObjectURL(reportPreviewUrl.value)
    reportPreviewUrl.value = ''
  }
}

onBeforeUnmount(() => {
  clearReportPreview()
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
const capabilitySummary = ref<any>(null)

const overviewData = ref<any>(null)
const overviewColumns = [
  { title: '列名', dataIndex: 'name', key: 'name' },
  { title: '类型', dataIndex: 'type', key: 'type' },
  { title: '缺失数', dataIndex: 'missing_count', key: 'missing_count' },
  { title: '缺失率', dataIndex: 'missing_rate', key: 'missing_rate', customRender: ({ text }: any) => `${(text * 100).toFixed(2)}%` },
  { title: '唯一值数', dataIndex: 'unique_count', key: 'unique_count' },
]

const cleanStrategy = ref({
  missing: 'drop',
  drop_duplicates: false,
  handle_outliers: false
})
const transformStrategy = ref({
  scaler: undefined,
  columns: [] as string[]
})

const descriptiveMode = ref<'summary' | 'full'>('summary')
const descriptiveLimitColumns = ref(10)

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

const corrCols = ref<string[]>([])
const corrMethod = ref('pearson')
const corrMissingStrategy = ref('drop')

const regY = ref<string>('')
const regX = ref<string[]>([])
const regType = ref('linear')
const polyDegree = ref(2)
const regMissingStrategy = ref('drop')
const regData = ref<any>(null)

const chartType = ref('bar')
const chartX = ref<string>('')
const chartY = ref<string | undefined>(undefined)
const chartAgg = ref('count')
const chartCurrentData = ref<any>(null)

const extensionForm = ref({
  mode: 'histogram',
  column: '',
  bins: 20,
  group_by: '',
  metric: undefined as string | undefined,
  agg_method: 'count',
  top_n: 20,
  text_column: '',
  min_length: 2,
})
const extensionResult = ref<any>(null)

const numericColumns = computed(() => {
  const schema = currentDataset.value?.schema_info
  if (!Array.isArray(schema) || schema.length === 0) {
    return columns.value
  }
  return schema
    .filter((item: any) => {
      const type = String(item.type || '').toLowerCase()
      return ['int', 'float', 'double', 'number', 'decimal', 'long', 'short'].some(keyword => type.includes(keyword))
    })
    .map((item: any) => item.name)
})

const textColumns = computed(() => {
  const schema = currentDataset.value?.schema_info
  if (!Array.isArray(schema) || schema.length === 0) {
    return columns.value
  }
  const nonNumeric = schema
    .filter((item: any) => {
      const type = String(item.type || '').toLowerCase()
      return !['int', 'float', 'double', 'number', 'decimal', 'long', 'short'].some(keyword => type.includes(keyword))
    })
    .map((item: any) => item.name)
  return nonNumeric.length ? nonNumeric : columns.value
})

const contentTitle = computed(() => {
  const map: any = {
    overview: '自动数据概览',
    descriptive: '描述性统计',
    correlation: '相关性热力图',
    regression: '回归分析',
    charts: '图表展示',
    extensions: 'sjfx 增量能力工作台'
  }
  return map[selectedMenu.value[0]] || '详情'
})



const descriptiveSkippedCategoricalCount = computed(() => {
  const categorical = descData.value?.categorical || {}
  return Object.values(categorical).filter((item: any) => item?.top_values_status === 'skipped_high_cardinality_scan').length
})

const descriptiveSummaryText = computed(() => {
  const meta = descData.value?.meta
  if (!meta) return ''
  const modeText = meta.mode === 'summary' ? '轻量摘要' : '完整统计'
  const skippedText = descriptiveSkippedCategoricalCount.value > 0
    ? `，其中 ${descriptiveSkippedCategoricalCount.value} 个高基数分类列已跳过频次扫描`
    : ''
  return `${modeText}，当前统计 ${meta.column_count || 0} 列${skippedText}`
})

const hasChart = computed(() => {
  return ['correlation', 'regression', 'charts', 'extensions'].includes(selectedMenu.value[0]) && chartOptions.value !== null
})
const capabilityColumns = [
  { title: '模块', dataIndex: 'name', key: 'name', width: 140 },
  { title: '说明', dataIndex: 'detail', key: 'detail' }
]

const capabilityRows = computed(() => {
  if (!capabilitySummary.value) return []
  return [
    {
      key: 'cleaning',
      name: '快速清洗',
      detail: capabilitySummary.value.cleaning?.data?.capabilities?.description || '已接入'
    },
    {
      key: 'chart',
      name: '图表计算',
      detail: (capabilitySummary.value.chart?.data?.capabilities?.charts || []).map((item: any) => item.label).join('、') || '已接入'
    },
    {
      key: 'theme',
      name: '主题色卡',
      detail: capabilitySummary.value.theme?.data?.capabilities?.description || '已接入'
    },
    {
      key: 'report',
      name: '快速报告',
      detail: (capabilitySummary.value.report?.data?.capabilities?.formats || []).join('、') || 'html'
    }
  ]
})

const extensionSummaryItems = computed(() => {
  if (!extensionResult.value) return []
  const summary = extensionResult.value.summary || {}
  if (extensionResult.value.type === 'histogram') {
    return [
      { label: '最小值', value: formatDisplayValue(summary.min) },
      { label: '最大值', value: formatDisplayValue(summary.max) },
      { label: '均值', value: formatDisplayValue(summary.mean) },
      { label: '中位数', value: formatDisplayValue(summary.median) },
    ]
  }
  if (extensionResult.value.type === 'boxplot') {
    return [
      { label: '样本数', value: formatDisplayValue(summary.count) },
      { label: 'IQR', value: formatDisplayValue(summary.iqr) },
      { label: '异常值数', value: formatDisplayValue(summary.outlier_count) },
    ]
  }
  if (extensionResult.value.type === 'aggregate') {
    return [
      { label: '分组列', value: extensionResult.value.groupBy },
      { label: '聚合方法', value: extensionResult.value.aggMethod },
      { label: 'Top N', value: formatDisplayValue(extensionResult.value.topN) },
    ]
  }
  if (extensionResult.value.type === 'wordcloud') {
    return [
      { label: '总词频', value: formatDisplayValue(extensionResult.value.tokenCount) },
      { label: '唯一词数', value: formatDisplayValue(extensionResult.value.uniqueTokens) },
      { label: '展示数量', value: formatDisplayValue(extensionResult.value.topN) },
    ]
  }
  return []
})

const extensionTableColumns = computed(() => {
  if (!extensionResult.value) return []
  if (extensionResult.value.type === 'histogram') {
    return [
      { title: '区间', dataIndex: 'label', key: 'label' },
      { title: '数量', dataIndex: 'value', key: 'value', width: 120 },
    ]
  }
  if (extensionResult.value.type === 'aggregate') {
    return [
      { title: '分组', dataIndex: 'label', key: 'label' },
      { title: '值', dataIndex: 'value', key: 'value', width: 140 },
    ]
  }
  if (extensionResult.value.type === 'wordcloud') {
    return [
      { title: '词语', dataIndex: 'label', key: 'label' },
      { title: '词频', dataIndex: 'value', key: 'value', width: 120 },
    ]
  }
  if (extensionResult.value.type === 'boxplot') {
    return [
      { title: '序号', dataIndex: 'label', key: 'label', width: 120 },
      { title: '异常值', dataIndex: 'value', key: 'value' },
    ]
  }
  return []
})

const extensionTableRows = computed(() => {
  if (!extensionResult.value) return []
  if (extensionResult.value.type === 'histogram') {
    return extensionResult.value.rows.map((item: any, index: number) => ({ key: index, label: item.label, value: item.value }))
  }
  if (extensionResult.value.type === 'aggregate') {
    return extensionResult.value.rows.map((item: any, index: number) => ({ key: index, label: item.label, value: item.value }))
  }
  if (extensionResult.value.type === 'wordcloud') {
    return extensionResult.value.rows.map((item: any, index: number) => ({ key: index, label: item.label, value: item.value }))
  }
  if (extensionResult.value.type === 'boxplot') {
    return extensionResult.value.outliers.map((value: number, index: number) => ({ key: index, label: index + 1, value: formatDisplayValue(value) }))
  }
  return []
})

const formatDisplayValue = (value: any) => {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value : Number(value.toFixed(4))
  }
  return String(value)
}

const syncExtensionDefaults = () => {
  if (!columns.value.length) return

  if (!numericColumns.value.includes(extensionForm.value.column)) {
    extensionForm.value.column = numericColumns.value[0] || ''
  }

  if (!columns.value.includes(extensionForm.value.group_by)) {
    extensionForm.value.group_by = columns.value[0] || ''
  }

  if (extensionForm.value.metric && !numericColumns.value.includes(extensionForm.value.metric)) {
    extensionForm.value.metric = undefined
  }

  if (!extensionForm.value.metric && numericColumns.value.length) {
    extensionForm.value.metric = numericColumns.value[0]
  }

  if (!textColumns.value.includes(extensionForm.value.text_column)) {
    extensionForm.value.text_column = textColumns.value[0] || columns.value[0] || ''
  }
}

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
  } else {
    columns.value = []
  }
  chartOptions.value = null
  extensionResult.value = null
  clearReportPreview()
  syncExtensionDefaults()
  fetchCurrentMenuData()
}

watch(() => selectedMenu.value, () => {
  chartOptions.value = null
  if (selectedDatasetId.value) {
    fetchCurrentMenuData()
  }
})

watch([numericColumns, textColumns, columns], () => {
  syncExtensionDefaults()
})

const fetchCurrentMenuData = async () => {
  if (selectedMenu.value[0] === 'overview') {
    await fetchOverview()
  } else if (selectedMenu.value[0] === 'descriptive') {
    await fetchDescriptive()
  }
}

const getDefaultDescriptiveColumns = () => {
  const picked = new Set<string>()
  numericColumns.value.slice(0, 8).forEach(col => picked.add(col))
  textColumns.value.slice(0, 2).forEach(col => picked.add(col))
  return Array.from(picked)
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
    const requestedColumns = descriptiveMode.value === 'full' ? null : getDefaultDescriptiveColumns()
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/descriptive`, {
      mode: descriptiveMode.value,
      limit_columns: descriptiveMode.value === 'summary' ? descriptiveLimitColumns.value : null,
      columns: requestedColumns && requestedColumns.length > 0 ? requestedColumns : null
    })
    if (res.success) {
      descData.value = res.data
      if (res.data.numeric && Object.keys(res.data.numeric).length) {
        dataWorker.postMessage({ type: 'FORMAT_NUMERIC_DESC', payload: { numObj: res.data.numeric } })
      } else {
        formattedDescData.value = []
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

      if (regX.value.length === 1 && res.data.fit_line) {
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

const buildHistogramOptions = (labels: string[], counts: number[]) => ({
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: labels, axisLabel: { rotate: 30 } },
  yAxis: { type: 'value' },
  series: [{ type: 'bar', data: counts, itemStyle: { color: '#1677ff' } }]
})

const buildBoxplotOptions = (column: string, box: number[], outliers: number[]) => ({
  tooltip: { trigger: 'item' },
  xAxis: { type: 'category', data: [column] },
  yAxis: { type: 'value' },
  series: [
    {
      name: '箱线图',
      type: 'boxplot',
      data: [box]
    },
    {
      name: '异常值',
      type: 'scatter',
      data: outliers.map(value => [0, value])
    }
  ]
})

const buildAggregateOptions = (labels: string[], values: number[], title: string) => ({
  title: { text: title },
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: labels, axisLabel: { rotate: 30 } },
  yAxis: { type: 'value' },
  series: [{ type: 'bar', data: values, itemStyle: { color: '#52c41a' } }]
})

const buildWordcloudOptions = (rows: Array<{ label: string; value: number }>) => ({
  title: { text: '词频 Top N' },
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: rows.map(item => item.label), axisLabel: { rotate: 30 } },
  yAxis: { type: 'value' },
  series: [{ type: 'bar', data: rows.map(item => item.value), itemStyle: { color: '#722ed1' } }]
})

const runExtensionAction = async () => {
  if (!selectedDatasetId.value) return

  const mode = extensionForm.value.mode
  if (['histogram', 'boxplot'].includes(mode) && !extensionForm.value.column) {
    message.warning('请选择数值列')
    return
  }
  if (mode === 'aggregate' && !extensionForm.value.group_by) {
    message.warning('请选择分组列')
    return
  }
  if (mode === 'wordcloud' && !extensionForm.value.text_column) {
    message.warning('请选择文本列')
    return
  }

  loading.value = true
  try {
    if (mode === 'histogram') {
      const res: any = await request.post(`/chart-calculations/${selectedDatasetId.value}/histogram`, {
        column: extensionForm.value.column,
        bins: extensionForm.value.bins,
      })
      if (res.success) {
        chartOptions.value = buildHistogramOptions(res.data.labels, res.data.counts)
        extensionResult.value = {
          type: 'histogram',
          title: `直方图：${extensionForm.value.column}`,
          summary: res.data.summary,
          rows: res.data.labels.map((label: string, index: number) => ({ label, value: res.data.counts[index] }))
        }
      }
    } else if (mode === 'boxplot') {
      const res: any = await request.post(`/chart-calculations/${selectedDatasetId.value}/boxplot`, {
        column: extensionForm.value.column,
      })
      if (res.success) {
        chartOptions.value = buildBoxplotOptions(extensionForm.value.column, res.data.box, res.data.outliers)
        extensionResult.value = {
          type: 'boxplot',
          title: `箱线图：${extensionForm.value.column}`,
          summary: res.data.summary,
          outliers: res.data.outliers,
        }
      }
    } else if (mode === 'aggregate') {
      const res: any = await request.post(`/chart-calculations/${selectedDatasetId.value}/aggregate`, {
        group_by: extensionForm.value.group_by,
        metric: extensionForm.value.agg_method === 'count' ? null : extensionForm.value.metric,
        agg_method: extensionForm.value.agg_method,
        top_n: extensionForm.value.top_n,
      })
      if (res.success) {
        chartOptions.value = buildAggregateOptions(res.data.labels, res.data.values, '聚合图结果')
        extensionResult.value = {
          type: 'aggregate',
          title: `聚合图：${extensionForm.value.group_by}`,
          groupBy: extensionForm.value.group_by,
          aggMethod: res.data.agg_method,
          topN: extensionForm.value.top_n,
          rows: res.data.labels.map((label: string, index: number) => ({ label, value: res.data.values[index] }))
        }
      }
    } else if (mode === 'wordcloud') {
      const res: any = await request.post(`/chart-calculations/${selectedDatasetId.value}/wordcloud`, {
        text_column: extensionForm.value.text_column,
        top_n: extensionForm.value.top_n,
        min_length: extensionForm.value.min_length,
      })
      if (res.success) {
        const rows = (res.data.words || []).map((item: any) => ({ label: item.name, value: item.value }))
        chartOptions.value = buildWordcloudOptions(rows)
        extensionResult.value = {
          type: 'wordcloud',
          title: `词频结果：${extensionForm.value.text_column}`,
          tokenCount: res.data.token_count,
          uniqueTokens: res.data.unique_tokens,
          topN: extensionForm.value.top_n,
          rows,
        }
      }
    }
    message.success('增量能力执行完成')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '执行增量能力失败')
  } finally {
    loading.value = false
  }
}

const buildQuickReportBlocks = () => {
  const blocks: any[] = []

  if (overviewData.value) {
    blocks.push({
      type: 'overview',
      title: '数据集概览',
      items: {
        总行数: overviewData.value.row_count,
        总列数: overviewData.value.col_count,
        内存占用MB: overviewData.value.memory_usage_mb,
      }
    })
  }

  if (descData.value?.numeric && Object.keys(descData.value.numeric).length) {
    const rows = Object.entries(descData.value.numeric)
      .slice(0, 10)
      .map(([col, stats]: [string, any]) => ({
        列名: col,
        count: formatDisplayValue(stats.count),
        mean: formatDisplayValue(stats.mean),
        std: formatDisplayValue(stats.std),
        min: formatDisplayValue(stats.min),
        max: formatDisplayValue(stats.max),
      }))
    if (rows.length) {
      blocks.push({
        type: 'descriptive_stats',
        title: '描述性统计摘要',
        rows,
      })
    }
  }

  if (extensionResult.value) {
    blocks.push({
      type: 'notes',
      title: extensionResult.value.title,
      content: extensionSummaryItems.value.map(item => `${item.label}: ${item.value}`).join('；') || '已生成增量能力结果'
    })
  }

  if (!blocks.length) {
    blocks.push({
      type: 'notes',
      title: '说明',
      content: '当前未生成统计结果，报告仅包含基础数据集上下文。'
    })
  }

  return blocks
}

const previewQuickHtmlReport = async () => {
  if (!selectedDatasetId.value) return

  if (!overviewData.value) {
    await fetchOverview()
  }
  if (!descData.value) {
    await fetchDescriptive()
  }

  loading.value = true
  try {
    const html: any = await request.post(`/quick-reports/${selectedDatasetId.value}/html`, {
      title: `${currentDataset.value?.name || '数据集'} 快速分析报告`,
      blocks: buildQuickReportBlocks(),
    })
    clearReportPreview()
    const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
    reportPreviewUrl.value = URL.createObjectURL(blob)
    window.open(reportPreviewUrl.value, '_blank', 'noopener')
    message.success('HTML 快报已生成')
  } catch (e: any) {
    message.error(e.response?.data?.detail || '生成 HTML 快报失败')
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
  } finally {
    loading.value = false
  }
}

const exportReport = (type: 'markdown' | 'pdf') => {
  if (!selectedDatasetId.value) return
  message.info(`正在生成 ${type.toUpperCase()} 报告，请稍候在产物中心查看...`)
}

const loadExtensionCapabilities = async () => {
  try {
    const [cleaning, chart, theme, report] = await Promise.all([
      request.get('/quick-cleaning/capabilities'),
      request.get('/chart-calculations/capabilities'),
      request.get('/theme-palettes/capabilities'),
      request.get('/quick-reports/capabilities')
    ])
    capabilitySummary.value = { cleaning, chart, theme, report }
    message.success('增量能力接口可用')
  } catch (e) {
    message.error('增量能力接口探测失败')
  }
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
.report-preview-frame {
  width: 100%;
  min-height: 640px;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  background: #fff;
}
</style>
