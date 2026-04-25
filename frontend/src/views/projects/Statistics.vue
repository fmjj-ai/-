<template>
  <div class="statistics-container">
    <a-row :gutter="24" class="full-height">
      <a-col :span="7" class="full-height">
        <a-card title="数据统计分析" :bordered="false" class="neumorphism-card full-height panel-scroll">
          <a-form layout="vertical">
            <DatasetSelector
              v-model="selectedDatasetId"
              :datasets="datasets"
              @change="onDatasetChange"
            />

            <a-menu
              v-if="selectedDatasetId"
              v-model:selectedKeys="selectedMenu"
              mode="inline"
              class="menu-panel"
            >
              <a-menu-item key="overview">自动数据概览</a-menu-item>
              <a-menu-item key="descriptive">描述性统计</a-menu-item>
              <a-menu-item key="correlation">相关性热力图</a-menu-item>
              <a-menu-item key="regression">回归分析</a-menu-item>
              <a-menu-item key="charts">图表展示</a-menu-item>
            </a-menu>

            <template v-if="selectedDatasetId && currentMenu === 'descriptive'">
              <DescriptiveForm
                :form="descriptiveForm"
                :columns="columns"
                :numeric-columns="numericColumns"
                :loading="loading"
                @refresh="fetchDescriptive"
                @generate-chart="generateDescriptiveChart"
              />
            </template>

            <template v-if="selectedDatasetId && currentMenu === 'correlation'">
              <CorrelationForm
                :form="correlationForm"
                :numeric-columns="numericColumns"
                :loading="loading"
                @run="fetchCorrelation"
              />
            </template>

            <template v-if="selectedDatasetId && currentMenu === 'regression'">
              <RegressionForm
                :form="regressionForm"
                :numeric-columns="numericColumns"
                :loading="loading"
                @run="fetchRegression"
              />
            </template>

            <template v-if="selectedDatasetId && currentMenu === 'charts'">
              <ChartsForm
                :form="chartsForm"
                :columns="columns"
                :numeric-columns="numericColumns"
                :loading="loading"
                @run="fetchChartData"
              />
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
            <OverviewPanel v-if="currentMenu === 'overview'" :data="overviewData" />

            <DescriptivePanel
              v-else-if="currentMenu === 'descriptive'"
              ref="activePanelRef"
              :data="descData"
              :chart-options="chartOptions"
            />

            <CorrelationPanel
              v-else-if="currentMenu === 'correlation'"
              ref="activePanelRef"
              :chart-options="chartOptions"
              :columns="heatmapColumns"
            />

            <RegressionPanel
              v-else-if="currentMenu === 'regression'"
              ref="activePanelRef"
              :data="regData"
              :chart-options="chartOptions"
            />

            <ChartsPanel
              v-else-if="currentMenu === 'charts'"
              ref="activePanelRef"
              :chart-options="chartOptions"
            />
          </div>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'

import DatasetSelector from '@/components/common/DatasetSelector.vue'
import DescriptiveForm from '@/components/statistics/DescriptiveForm.vue'
import CorrelationForm from '@/components/statistics/CorrelationForm.vue'
import RegressionForm from '@/components/statistics/RegressionForm.vue'
import ChartsForm from '@/components/statistics/ChartsForm.vue'
import OverviewPanel from '@/components/statistics/OverviewPanel.vue'
import DescriptivePanel from '@/components/statistics/DescriptivePanel.vue'
import CorrelationPanel from '@/components/statistics/CorrelationPanel.vue'
import RegressionPanel from '@/components/statistics/RegressionPanel.vue'
import ChartsPanel from '@/components/statistics/ChartsPanel.vue'

import request from '@/utils/request'
import {
  buildBoxplotOptions,
  buildCorrelationHeatmapOptions,
  buildGenericChartOptions,
  buildHistogramOptions,
  buildWordFreqOptions,
} from '@/utils/chartOptions'

import { useAsyncAction } from '@/composables/useAsyncAction'
import { useDatasets } from '@/composables/useDatasets'
import { useChartArtifactExport } from '@/composables/useChartArtifactExport'

// ========== 基础上下文 ==========
const route = useRoute()
const projectId = computed(() => String(route.params.projectId || ''))

const { loading, run: runWithLoading, showError } = useAsyncAction()
const reportLoading = ref(false)

// ========== 数据集 ==========
const {
  datasets,
  selectedDatasetId,
  currentDataset,
  columns,
  numericColumns,
  fetchDatasets,
  handleChange,
} = useDatasets(() => projectId.value, {
  onChange: () => {
    resetDatasetState()
    return fetchCurrentMenuData()
  },
})

// ========== 菜单 ==========
const selectedMenu = ref(['overview'])
const currentMenu = computed(() => selectedMenu.value[0] || 'overview')

const menuTitleMap: Record<string, string> = {
  overview: '自动数据概览',
  descriptive: '描述性统计与可视化',
  correlation: '相关性热力图',
  regression: '回归分析',
  charts: '图表展示',
}
const contentTitle = computed(() => menuTitleMap[currentMenu.value] || '数据统计')

// ========== 各面板状态 ==========
const overviewData = ref<any | null>(null)
const descData = ref<any | null>(null)
const regData = ref<any | null>(null)
const chartOptions = ref<any | null>(null)
const heatmapColumns = ref<string[]>([])

// 当前活动面板组件 ref（面板都 exposeGetChartDataUrl / resize）
const activePanelRef = ref<any>(null)

const descriptiveForm = reactive({
  mode: 'summary' as 'summary' | 'full',
  limitColumns: 10,
  viz: {
    column: '',
    type: 'histogram',
    color: '#1677ff',
    shape: 'circle',
    bins: 20,
    topN: 30,
    minLength: 2,
  },
})

const correlationForm = reactive({
  columns: [] as string[],
  method: 'pearson' as 'pearson' | 'spearman' | 'kendall',
})

const regressionForm = reactive({
  y: '',
  x: [] as string[],
  type: 'linear' as 'linear' | 'polynomial',
  polyDegree: 2,
})

const chartsForm = reactive({
  type: 'bar' as 'bar' | 'line' | 'pie' | 'bar3D',
  x: '',
  y: undefined as string | undefined,
  agg: 'count' as 'count' | 'sum' | 'mean',
  color: '#4f7cff',
})

// ========== 图表导出 ==========
const { exportChartArtifact } = useChartArtifactExport({
  chartRefGetter: () => activePanelRef.value,
  projectId: () => projectId.value,
  buildFileName: (type) => {
    const datasetName = currentDataset.value?.name || '数据集'
    const actionNameMap: Record<string, string> = {
      descriptive: '描述性分析图',
      correlation: '相关性热力图',
      regression: '回归分析图',
      charts: '统计图表',
    }
    return `${datasetName}${actionNameMap[currentMenu.value] || '图表'}.${type}`
  },
})

// ========== 状态重置 ==========
const resetChartState = () => {
  chartOptions.value = null
  heatmapColumns.value = []
}

const resetDatasetState = () => {
  regressionForm.y = ''
  regressionForm.x = []
  chartsForm.x = ''
  chartsForm.y = undefined
  overviewData.value = null
  descData.value = null
  regData.value = null
  resetChartState()
  descriptiveForm.viz.column = columns.value[0] || ''
}

const onDatasetChange = async () => {
  await handleChange()
}

// ========== 面板数据获取 ==========
const fetchCurrentMenuData = async () => {
  if (currentMenu.value === 'overview') {
    await fetchOverview()
  } else if (currentMenu.value === 'descriptive') {
    await fetchDescriptive()
  }
}

watch(
  () => currentMenu.value,
  async () => {
    resetChartState()
    if (selectedDatasetId.value) {
      await fetchCurrentMenuData()
    }
  }
)

const fetchOverview = async () => {
  if (!selectedDatasetId.value) return
  await runWithLoading(async () => {
    const res: any = await request.get(`/statistics/${selectedDatasetId.value}/overview`)
    if (res.success) {
      overviewData.value = res.data
    }
  }, '获取概览失败')
}

const fetchDescriptive = async () => {
  if (!selectedDatasetId.value) return
  await runWithLoading(async () => {
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/descriptive`, {
      mode: descriptiveForm.mode,
      limit_columns: descriptiveForm.mode === 'summary' ? descriptiveForm.limitColumns : null,
      columns:
        descriptiveForm.mode === 'summary'
          ? columns.value.slice(0, descriptiveForm.limitColumns)
          : null,
    })
    if (res.success) {
      descData.value = res.data
    }
  }, '获取描述性统计失败')
}

const generateDescriptiveChart = async () => {
  if (!selectedDatasetId.value || !descriptiveForm.viz.column) {
    message.warning('请选择用于可视化的目标列')
    return
  }
  await runWithLoading(async () => {
    const { viz } = descriptiveForm
    if (viz.type === 'histogram') {
      const res: any = await request.post(
        `/chart-calculations/${selectedDatasetId.value}/histogram`,
        { column: viz.column, bins: viz.bins }
      )
      if (res.success) {
        chartOptions.value = buildHistogramOptions(res.data.labels, res.data.counts, viz.color)
      }
    } else if (viz.type === 'boxplot') {
      const res: any = await request.post(
        `/chart-calculations/${selectedDatasetId.value}/boxplot`,
        { column: viz.column }
      )
      if (res.success) {
        chartOptions.value = buildBoxplotOptions(
          viz.column,
          res.data.box,
          res.data.outliers,
          viz.color,
          viz.shape
        )
      }
    } else {
      const res: any = await request.post(
        `/chart-calculations/${selectedDatasetId.value}/wordcloud`,
        { text_column: viz.column, top_n: viz.topN, min_length: viz.minLength }
      )
      if (res.success) {
        const rows = (res.data.words || []).map((item: any) => ({
          label: item.name,
          value: item.value,
        }))
        chartOptions.value = buildWordFreqOptions(rows, viz.color)
      }
    }
  }, '生成描述性可视化失败')
}

const fetchCorrelation = async () => {
  if (!selectedDatasetId.value) return
  resetChartState()
  await runWithLoading(async () => {
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/correlation`, {
      columns: correlationForm.columns.length > 0 ? correlationForm.columns : null,
      method: correlationForm.method,
    })
    if (res.success) {
      const data = res.data
      heatmapColumns.value = data.columns || []
      chartOptions.value = buildCorrelationHeatmapOptions(data)
      nextTick(() => {
        requestAnimationFrame(() => {
          activePanelRef.value?.resize?.()
        })
      })
    }
  }, '计算热力图失败')
}

const fetchRegression = async () => {
  if (!selectedDatasetId.value || !regressionForm.y || regressionForm.x.length === 0) {
    message.warning('请选择因变量和自变量')
    return
  }
  await runWithLoading(async () => {
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/regression`, {
      y_col: regressionForm.y,
      x_cols: regressionForm.x,
      reg_type: regressionForm.type,
      poly_degree: regressionForm.polyDegree,
    })
    if (res.success) {
      regData.value = res.data
      if (regressionForm.x.length === 1 && res.data.fit_line) {
        chartOptions.value = {
          tooltip: { trigger: 'axis' },
          xAxis: { type: 'value', name: regressionForm.x[0] },
          yAxis: { type: 'value', name: regressionForm.y },
          series: [
            {
              name: '拟合线',
              type: 'line',
              showSymbol: false,
              data: res.data.fit_line,
              lineStyle: { width: 3, color: chartsForm.color },
            },
          ],
        }
      } else {
        chartOptions.value = null
      }
    }
  }, '回归分析失败')
}

const fetchChartData = async () => {
  if (!selectedDatasetId.value || !chartsForm.x) {
    message.warning('请选择 X 轴 / 分组列')
    return
  }
  await runWithLoading(async () => {
    const res: any = await request.post(`/statistics/${selectedDatasetId.value}/aggregation`, {
      x_col: chartsForm.x,
      y_col: chartsForm.y || null,
      agg_method: chartsForm.agg,
      max_bins: 50,
    })
    if (res.success) {
      chartOptions.value = buildGenericChartOptions(res.data, chartsForm.type, chartsForm.color)
    }
  }, '生成图表失败')
}

// ========== 报告导出 ==========
const buildReportBlocks = async () => {
  const blocks: any[] = []
  if (overviewData.value) {
    blocks.push({
      type: 'text',
      content: `数据集总行数：${overviewData.value.row_count}，总列数：${overviewData.value.col_count}`,
    })
  }
  if (descData.value?.numeric) {
    const firstNumericColumn = Object.keys(descData.value.numeric)[0]
    if (firstNumericColumn) {
      blocks.push({
        type: 'table',
        title: `${firstNumericColumn} 描述性统计`,
        data: descData.value.numeric[firstNumericColumn],
      })
    }
  }
  if (chartOptions.value) {
    const dataUrl = activePanelRef.value?.getChartDataUrl?.('png', false, 2)
    if (dataUrl) {
      blocks.push({ type: 'chart', title: contentTitle.value, image_url: dataUrl })
    }
  }
  if (!blocks.length) {
    blocks.push({
      type: 'text',
      content: '当前页面暂无可写入报告的结果，请先生成统计结果或图表。',
    })
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
      content_blocks: blocks,
    })
    if (res.success) {
      message.success(`报告已生成并进入导出中心：${res.data.name}`)
    }
  } catch (error: any) {
    showError(error, '报告生成失败')
  } finally {
    reportLoading.value = false
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
</style>
