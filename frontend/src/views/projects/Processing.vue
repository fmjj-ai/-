<template>
  <div class="processing-container">
    <a-row :gutter="24" class="full-height">
      <a-col :span="7" class="full-height">
        <a-card title="数据处理与建模" :bordered="false" class="neumorphism-card full-height panel-scroll">
          <a-form layout="vertical">
            <DatasetSelector
              v-model="selectedDatasetId"
              :datasets="datasets"
              @change="onDatasetChange"
            />

            <a-collapse v-if="selectedDatasetId" v-model:activeKey="activeKey">
              <a-collapse-panel key="cleaning" header="数据清洗">
                <CleaningForm
                  :form="quickCleanOp"
                  :numeric-columns="numericColumns"
                  :processing="processing"
                  @load-missing-stats="loadMissingStats"
                  @preview-outliers="previewOutliers"
                  @apply-outliers="applyQuickOutlierHandling"
                />
              </a-collapse-panel>

              <a-collapse-panel key="transform" header="数据变换">
                <TransformForm
                  :form="transformOp"
                  :numeric-columns="numericColumns"
                  :processing="processing"
                  @apply="applyTransformOp"
                />
              </a-collapse-panel>

              <a-collapse-panel key="encoding" header="特征编码">
                <EncodingForm
                  :form="encodeOp"
                  :columns="columns"
                  :processing="processing"
                  @preview="previewEncoding"
                />
              </a-collapse-panel>

              <a-collapse-panel key="cluster" header="聚类分析">
                <ClusterForm
                  :form="clusterOp"
                  :numeric-columns="numericColumns"
                  :processing="processing"
                  @run="applyClustering"
                />
              </a-collapse-panel>

              <a-collapse-panel key="modeling" header="分类与回归建模">
                <ModelingForm
                  :form="mlOp"
                  :columns="columns"
                  :numeric-columns="numericColumns"
                  :processing="processing"
                  @run="applyPredictiveModeling"
                />
              </a-collapse-panel>
            </a-collapse>
          </a-form>
        </a-card>
      </a-col>

      <a-col :span="17" class="full-height">
        <a-card title="处理与建模结果" :bordered="false" class="neumorphism-card full-height panel-scroll">
          <a-tabs v-model:activeKey="activeTab">
            <a-tab-pane key="data" tab="数据预览">
              <a-skeleton active :loading="tableLoading" :paragraph="{ rows: 10 }">
                <DataPreviewTable
                  :columns="tableColumns"
                  :data-source="tableData"
                  :pagination="pagination"
                  size="small"
                  row-key="_row_index"
                  :scroll="{ x: 'max-content' }"
                  @change="handleTableChange"
                />
              </a-skeleton>
            </a-tab-pane>

            <a-tab-pane key="cleaning" tab="异常值与清洗">
              <CleaningResultTab
                :missing-stats="missingStats"
                :outlier-preview="outlierPreview"
                :outlier-chart-options="outlierChartOptions"
              />
            </a-tab-pane>

            <a-tab-pane key="encoding" tab="编码预览">
              <EncodingResultTab :preview="lastEncodingPreview" />
            </a-tab-pane>

            <a-tab-pane key="model_results" tab="建模结果">
              <ModelResultsTab :tasks="modelingTasks" />
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>
    </a-row>

    <EncodingPreviewModal
      v-model:open="encodingPreviewVisible"
      v-model:selected-mode="encodingSelectedMode"
      :preview="encodingPreviewData"
      :ordinal-mapping-rows="ordinalMappingRows"
      :processing="processing"
      @confirm="confirmEncoding"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'

import DatasetSelector from '@/components/common/DatasetSelector.vue'
import DataPreviewTable from '@/components/DataPreviewTable.vue'
import CleaningForm from '@/components/processing/CleaningForm.vue'
import TransformForm from '@/components/processing/TransformForm.vue'
import EncodingForm from '@/components/processing/EncodingForm.vue'
import ClusterForm from '@/components/processing/ClusterForm.vue'
import ModelingForm from '@/components/processing/ModelingForm.vue'
import CleaningResultTab from '@/components/processing/CleaningResultTab.vue'
import EncodingResultTab from '@/components/processing/EncodingResultTab.vue'
import ModelResultsTab from '@/components/processing/ModelResultsTab.vue'
import EncodingPreviewModal from '@/components/processing/EncodingPreviewModal.vue'

import request from '@/utils/request'
import { useTaskStore } from '@/store/modules/task'
import { useAsyncAction } from '@/composables/useAsyncAction'
import { useDatasets } from '@/composables/useDatasets'

const route = useRoute()
const taskStore = useTaskStore()

const projectId = computed(() => String(route.params.projectId || ''))

const { loading: processing, run: runProcessingTask, showError } = useAsyncAction()

const {
  datasets,
  selectedDatasetId,
  currentDataset,
  columns,
  numericColumns,
  fetchDatasets,
  handleChange,
} = useDatasets(() => projectId.value, {
  onChange: async () => {
    resetPreviewState()
    updateColumnsList()
    pagination.value.current = 1
    await fetchTableData()
    await fetchTaskList()
  },
})

const tableColumns = ref<any[]>([])
const tableData = ref<any[]>([])
const tableLoading = ref(false)
const activeKey = ref(['cleaning'])
const activeTab = ref('data')

const pagination = ref({
  current: 1,
  pageSize: 50,
  total: 0,
  showSizeChanger: true,
})

const missingStats = ref<any | null>(null)
const outlierPreview = ref<any | null>(null)
const outlierChartOptions = ref<any | null>(null)
const lastEncodingPreview = ref<any | null>(null)
const encodingPreviewVisible = ref(false)
const encodingPreviewData = ref<any | null>(null)
const encodingSelectedMode = ref('ordinal_encode')
const ordinalMappingRows = ref<any[]>([])

const quickCleanOp = reactive({
  column: '',
  method: 'iqr' as 'iqr' | 'zscore',
  strategy: 'clip' as 'clip' | 'remove' | 'replace_mean',
  z_threshold: 3,
})

const transformOp = reactive({
  type: 'compute_column' as 'compute_column' | 'normalize',
  new_column: '',
  expression: '',
  columns: [] as string[],
  method: 'minmax' as 'minmax' | 'zscore',
})

const encodeOp = reactive({
  column: '',
  separator: ',',
  keep_original: true,
})

const clusterOp = reactive({
  algorithm: 'kmeans' as 'kmeans' | 'dbscan' | 'hdbscan' | 'meanshift',
  features: [] as string[],
  auto_k: true,
  k: 3,
  k_min: 2,
  k_max: 10,
  eps: 0.5,
  min_samples: 5,
  min_cluster_size: 5,
  bandwidth: undefined as number | undefined,
})

const mlOp = reactive({
  task_type: 'classification' as 'classification' | 'regression',
  algorithm: 'rf' as 'rf' | 'xgb' | 'lgbm' | 'mlp',
  target_col: '',
  feature_cols: [] as string[],
  test_size: 0.2,
})

const modelingTasks = computed(() => {
  if (!selectedDatasetId.value) return []
  return [...taskStore.tasks]
    .filter(
      (task) =>
        task.status === 'completed' && task.result?.dataset_id === selectedDatasetId.value
    )
    .filter((task) => ['clustering', 'predictive_modeling'].includes(task.result?.kind))
    .sort(
      (a, b) =>
        new Date(b.finished_at || b.created_at || 0).getTime() -
        new Date(a.finished_at || a.created_at || 0).getTime()
    )
})

const resetPreviewState = () => {
  missingStats.value = null
  outlierPreview.value = null
  outlierChartOptions.value = null
}

const buildTableColumns = (columnNames: string[]) =>
  columnNames.map((column) => ({ title: column, dataIndex: column, key: column, width: 160 }))

const updateColumnsList = () => {
  tableColumns.value = buildTableColumns(columns.value)
  if (!quickCleanOp.column || !numericColumns.value.includes(quickCleanOp.column)) {
    quickCleanOp.column = numericColumns.value[0] || ''
  }
  if (!encodeOp.column) {
    encodeOp.column = columns.value[0] || ''
  }
}

const fetchTaskList = async () => {
  if (!projectId.value) return
  await taskStore.fetchTasks(projectId.value)
}

const onDatasetChange = async () => {
  await handleChange()
}

const fetchTableData = async () => {
  if (!selectedDatasetId.value) return
  tableLoading.value = true
  try {
    const res: any = await request.get(`/datasets/${selectedDatasetId.value}/data`, {
      params: { page: pagination.value.current, size: pagination.value.pageSize },
    })
    if (res.success) {
      tableData.value = res.data.items || []
      pagination.value.total = res.data.total || 0
    }
  } catch (error: any) {
    showError(error, '获取表格数据失败')
  } finally {
    tableLoading.value = false
  }
}

const handleTableChange = (pageInfo: any) => {
  pagination.value.current = pageInfo.current
  pagination.value.pageSize = pageInfo.pageSize
  fetchTableData()
}

const refreshCurrentDataset = async () => {
  if (!selectedDatasetId.value) return
  const res: any = await request.get(`/datasets/${selectedDatasetId.value}`)
  if (res.success) {
    currentDataset.value = res.data
    updateColumnsList()
  }
}

const refreshDatasetView = async () => {
  await refreshCurrentDataset()
  await fetchTableData()
}

const executeOperation = async (operation: any) => {
  if (!selectedDatasetId.value) return
  await runProcessingTask(async () => {
    const res: any = await request.post(
      `/processing/${selectedDatasetId.value}/process`,
      [operation]
    )
    if (res.success) {
      message.success('操作成功')
      await refreshDatasetView()
    }
  }, '处理失败')
}

const loadMissingStats = async () => {
  if (!selectedDatasetId.value) return
  await runProcessingTask(async () => {
    const res: any = await request.get(
      `/quick-cleaning/${selectedDatasetId.value}/missing-stats`
    )
    if (res.success) {
      missingStats.value = res.data
      activeTab.value = 'cleaning'
      message.success('缺失值统计已加载')
    }
  }, '获取缺失值统计失败')
}

const buildOutlierChartOptions = () => {
  const samples = (outlierPreview.value?.sample_values || []) as number[]
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: samples.map((_, i) => `样例${i + 1}`) },
    yAxis: { type: 'value' },
    series: [
      {
        type: 'bar',
        data: samples,
        itemStyle: { color: '#f59f00', borderRadius: [8, 8, 0, 0] },
      },
    ],
  }
}

const previewOutliers = async () => {
  if (!selectedDatasetId.value || !quickCleanOp.column) {
    message.warning('请选择异常值目标列')
    return
  }
  await runProcessingTask(async () => {
    const res: any = await request.post(
      `/quick-cleaning/${selectedDatasetId.value}/outlier-preview`,
      {
        column: quickCleanOp.column,
        method: quickCleanOp.method,
        z_threshold: quickCleanOp.z_threshold,
      }
    )
    if (res.success) {
      outlierPreview.value = res.data
      outlierChartOptions.value = buildOutlierChartOptions()
      activeTab.value = 'cleaning'
      message.success('异常值预览已更新')
    }
  }, '异常值预览失败')
}

const applyQuickOutlierHandling = async () => {
  if (!selectedDatasetId.value || !quickCleanOp.column) {
    message.warning('请选择异常值目标列')
    return
  }
  await runProcessingTask(async () => {
    const res: any = await request.post(
      `/quick-cleaning/${selectedDatasetId.value}/outlier-handle`,
      {
        column: quickCleanOp.column,
        method: quickCleanOp.method,
        strategy: quickCleanOp.strategy,
        z_threshold: quickCleanOp.z_threshold,
      }
    )
    if (res.success) {
      message.success(`异常值处理完成，影响 ${res.data.affected_rows} 行`)
      await refreshDatasetView()
      await loadMissingStats()
      await previewOutliers()
    }
  }, '异常值处理失败')
}

const applyTransformOp = async () => {
  const op = { type: transformOp.type, params: { ...transformOp } }
  await executeOperation(op)
}

const previewEncoding = async () => {
  if (!selectedDatasetId.value || !encodeOp.column) {
    message.warning('请选择需要编码的列')
    return
  }
  await runProcessingTask(async () => {
    const res: any = await request.post(
      `/processing/${selectedDatasetId.value}/encoding-preview`,
      { column: encodeOp.column, separator: encodeOp.separator }
    )
    if (res.success) {
      encodingPreviewData.value = res.data
      encodingSelectedMode.value = res.data.recommended_encoding
      ordinalMappingRows.value = Object.entries(res.data.recommended_mapping || {}).map(
        ([value, encoded]) => ({ value, encoded })
      )
      encodingPreviewVisible.value = true
      lastEncodingPreview.value = res.data
      activeTab.value = 'encoding'
    }
  }, '生成编码预览失败')
}

const buildEncodingOperation = () => {
  const column = encodingPreviewData.value?.column
  if (!column) return null

  if (encodingSelectedMode.value === 'ordinal_encode') {
    const mapping = Object.fromEntries(
      ordinalMappingRows.value.map((item) => [item.value, Number(item.encoded)])
    )
    return {
      type: 'ordinal_encode',
      params: {
        column,
        keep_original: encodeOp.keep_original,
        mapping,
        encoded_column: `${column}_编码`,
      },
    }
  }

  if (encodingSelectedMode.value === 'multi_hot_encode') {
    return {
      type: 'multi_hot_encode',
      params: {
        column,
        separator: encodeOp.separator,
        keep_original: encodeOp.keep_original,
      },
    }
  }

  return {
    type: 'one_hot_encode',
    params: {
      columns: [column],
      keep_original: encodeOp.keep_original,
    },
  }
}

const confirmEncoding = async () => {
  if (!encodingPreviewData.value) return
  const operation = buildEncodingOperation()
  if (!operation) return

  encodingPreviewVisible.value = false
  await executeOperation(operation)
  message.success('编码处理完成')
}

const applyClustering = async () => {
  if (!selectedDatasetId.value || clusterOp.features.length === 0) {
    message.warning('请选择聚类特征列')
    return
  }
  await runProcessingTask(async () => {
    const payload = {
      features: clusterOp.features,
      algorithm: clusterOp.algorithm,
      n_clusters: clusterOp.auto_k ? 0 : clusterOp.k,
      k_min: clusterOp.k_min,
      k_max: clusterOp.k_max,
      eps: clusterOp.eps,
      min_samples: clusterOp.min_samples,
      min_cluster_size: clusterOp.min_cluster_size,
      bandwidth: clusterOp.bandwidth,
    }
    const res: any = await request.post(
      `/modeling/${selectedDatasetId.value}/clustering`,
      payload
    )
    if (res.success) {
      await fetchTaskList()
      activeTab.value = 'model_results'
      message.success('聚类任务已提交')
    }
  }, '聚类任务提交失败')
}

const applyPredictiveModeling = async () => {
  if (!selectedDatasetId.value || !mlOp.target_col) {
    message.warning('请选择目标列')
    return
  }
  const fallbackFeatures = numericColumns.value.filter(
    (column: string) => column !== mlOp.target_col
  )
  const features = mlOp.feature_cols.length ? mlOp.feature_cols : fallbackFeatures
  if (!features.length) {
    message.warning('当前没有可用的数值特征列')
    return
  }
  await runProcessingTask(async () => {
    const res: any = await request.post(
      `/modeling/${selectedDatasetId.value}/predictive`,
      {
        target: mlOp.target_col,
        features,
        task_type: mlOp.task_type,
        algorithm: mlOp.algorithm,
        test_size: mlOp.test_size,
      }
    )
    if (res.success) {
      await fetchTaskList()
      activeTab.value = 'model_results'
      message.success('建模任务已提交')
    }
  }, '建模任务提交失败')
}

const handleTaskUpdate = async (event: MessageEvent) => {
  if (event.data === 'ping' || !selectedDatasetId.value) return
  try {
    const payload = JSON.parse(event.data)
    const result = payload.result || {}
    if (payload.status !== 'completed') return
    if (result.dataset_id !== selectedDatasetId.value) return
    if (!['clustering', 'predictive_modeling'].includes(result.kind)) return

    await fetchTaskList()
    await refreshCurrentDataset()
    await fetchTableData()
    activeTab.value = 'model_results'
    message.success(
      `${payload.status === 'completed' ? '任务已完成' : '任务状态已更新'}：${payload.task_id}`
    )
  } catch (error) {
    console.error('Processing task parse failed', error)
  }
}

onMounted(async () => {
  await fetchDatasets()
  await fetchTaskList()
  taskStore.connectSSE()
  taskStore.eventSource?.addEventListener('message', handleTaskUpdate)
})

onBeforeUnmount(() => {
  taskStore.eventSource?.removeEventListener('message', handleTaskUpdate)
})
</script>

<style scoped>
.processing-container {
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
</style>
