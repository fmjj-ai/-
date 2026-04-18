<template>
  <div class="processing-container">
    <a-row :gutter="24" class="full-height">
      <a-col :span="7" class="full-height">
        <a-card title="数据处理与建模" :bordered="false" class="neumorphism-card full-height panel-scroll">
          <a-form layout="vertical">
            <a-form-item label="选择数据集">
              <a-select v-model:value="selectedDatasetId" placeholder="请选择数据集" @change="handleDatasetChange">
                <a-select-option v-for="dataset in datasets" :key="dataset.id" :value="dataset.id">
                  {{ dataset.name }}
                </a-select-option>
              </a-select>
            </a-form-item>

            <a-collapse v-if="selectedDatasetId" v-model:activeKey="activeKey">
              <a-collapse-panel key="cleaning" header="数据清洗">
                <a-space direction="vertical" style="width: 100%">
                  <a-button block @click="loadMissingStats" :loading="processing">查看缺失值统计</a-button>
                  <a-form-item label="异常值目标列" style="margin-bottom: 0">
                    <a-select v-model:value="quickCleanOp.column" placeholder="选择数值列">
                      <a-select-option v-for="column in numericColumns" :key="column" :value="column">
                        {{ column }}
                      </a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-row :gutter="12">
                    <a-col :span="12">
                      <a-form-item label="检测方法" style="margin-bottom: 0">
                        <a-select v-model:value="quickCleanOp.method">
                          <a-select-option value="iqr">IQR</a-select-option>
                          <a-select-option value="zscore">Z-Score</a-select-option>
                        </a-select>
                      </a-form-item>
                    </a-col>
                    <a-col :span="12" v-if="quickCleanOp.method === 'zscore'">
                      <a-form-item label="Z 阈值" style="margin-bottom: 0">
                        <a-input-number v-model:value="quickCleanOp.z_threshold" :min="0.5" :step="0.5" style="width: 100%" />
                      </a-form-item>
                    </a-col>
                  </a-row>
                  <a-form-item label="处理策略" style="margin-bottom: 0">
                    <a-select v-model:value="quickCleanOp.strategy">
                      <a-select-option value="clip">截断到边界</a-select-option>
                      <a-select-option value="remove">删除异常行</a-select-option>
                      <a-select-option value="replace_mean">替换为均值</a-select-option>
                    </a-select>
                  </a-form-item>
                  <div class="split-action-row">
                    <a-button block @click="previewOutliers" :loading="processing">异常值预览</a-button>
                    <a-button type="primary" block @click="applyQuickOutlierHandling" :loading="processing">异常值处理</a-button>
                  </div>
                </a-space>
              </a-collapse-panel>

              <a-collapse-panel key="transform" header="数据变换">
                <a-form-item label="操作类型">
                  <a-select v-model:value="transformOp.type">
                    <a-select-option value="compute_column">新增计算列</a-select-option>
                    <a-select-option value="normalize">标准化 / 归一化</a-select-option>
                  </a-select>
                </a-form-item>

                <template v-if="transformOp.type === 'compute_column'">
                  <a-form-item label="新列名">
                    <a-input v-model:value="transformOp.new_column" />
                  </a-form-item>
                  <a-form-item label="表达式">
                    <a-input v-model:value="transformOp.expression" placeholder="例如：colA + colB" />
                  </a-form-item>
                </template>

                <template v-else>
                  <a-form-item label="目标列">
                    <a-select v-model:value="transformOp.columns" mode="multiple">
                      <a-select-option v-for="column in numericColumns" :key="column" :value="column">
                        {{ column }}
                      </a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item label="标准化方法">
                    <a-select v-model:value="transformOp.method">
                      <a-select-option value="minmax">Min-Max 归一化</a-select-option>
                      <a-select-option value="zscore">Z-Score 标准化</a-select-option>
                    </a-select>
                  </a-form-item>
                </template>

                <a-button type="primary" block @click="applyTransformOp" :loading="processing">应用变换</a-button>
              </a-collapse-panel>

              <a-collapse-panel key="encoding" header="特征编码">
                <a-form-item label="目标列">
                  <a-select v-model:value="encodeOp.column" placeholder="选择需要编码的列">
                    <a-select-option v-for="column in columns" :key="column" :value="column">
                      {{ column }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="多值分隔符">
                  <a-input v-model:value="encodeOp.separator" placeholder="默认为 ," />
                </a-form-item>
                <a-form-item>
                  <a-checkbox v-model:checked="encodeOp.keep_original">保留原始列</a-checkbox>
                </a-form-item>
                <a-button type="primary" block @click="previewEncoding" :loading="processing">预览并应用编码</a-button>
              </a-collapse-panel>

              <a-collapse-panel key="cluster" header="聚类分析">
                <a-form-item label="聚类算法">
                  <a-select v-model:value="clusterOp.algorithm">
                    <a-select-option value="kmeans">K-Means</a-select-option>
                    <a-select-option value="dbscan">DBSCAN</a-select-option>
                    <a-select-option value="hdbscan">HDBSCAN</a-select-option>
                    <a-select-option value="meanshift">MeanShift</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="特征列">
                  <a-select v-model:value="clusterOp.features" mode="multiple" placeholder="选择数值特征列">
                    <a-select-option v-for="column in numericColumns" :key="column" :value="column">
                      {{ column }}
                    </a-select-option>
                  </a-select>
                </a-form-item>

                <template v-if="clusterOp.algorithm === 'kmeans'">
                  <a-form-item>
                    <a-checkbox v-model:checked="clusterOp.auto_k">自动寻找最佳 K 值</a-checkbox>
                  </a-form-item>
                  <template v-if="clusterOp.auto_k">
                    <a-row :gutter="12">
                      <a-col :span="12">
                        <a-form-item label="最小 K">
                          <a-input-number v-model:value="clusterOp.k_min" :min="2" style="width: 100%" />
                        </a-form-item>
                      </a-col>
                      <a-col :span="12">
                        <a-form-item label="最大 K">
                          <a-input-number v-model:value="clusterOp.k_max" :min="3" style="width: 100%" />
                        </a-form-item>
                      </a-col>
                    </a-row>
                  </template>
                  <a-form-item v-else label="K 值">
                    <a-input-number v-model:value="clusterOp.k" :min="2" :max="20" style="width: 100%" />
                  </a-form-item>
                </template>

                <template v-if="clusterOp.algorithm === 'dbscan'">
                  <a-row :gutter="12">
                    <a-col :span="12">
                      <a-form-item label="eps">
                        <a-input-number v-model:value="clusterOp.eps" :min="0.1" :step="0.1" style="width: 100%" />
                      </a-form-item>
                    </a-col>
                    <a-col :span="12">
                      <a-form-item label="min_samples">
                        <a-input-number v-model:value="clusterOp.min_samples" :min="1" style="width: 100%" />
                      </a-form-item>
                    </a-col>
                  </a-row>
                </template>

                <template v-if="clusterOp.algorithm === 'hdbscan'">
                  <a-form-item label="min_cluster_size">
                    <a-input-number v-model:value="clusterOp.min_cluster_size" :min="2" style="width: 100%" />
                  </a-form-item>
                </template>

                <template v-if="clusterOp.algorithm === 'meanshift'">
                  <a-form-item label="bandwidth">
                    <a-input-number v-model:value="clusterOp.bandwidth" :min="0" :step="0.1" style="width: 100%" />
                  </a-form-item>
                </template>

                <a-button type="primary" block @click="applyClustering" :loading="processing">运行聚类</a-button>
              </a-collapse-panel>

              <a-collapse-panel key="modeling" header="分类与回归建模">
                <a-form-item label="任务类型">
                  <a-select v-model:value="mlOp.task_type">
                    <a-select-option value="classification">分类</a-select-option>
                    <a-select-option value="regression">回归</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="模型算法">
                  <a-select v-model:value="mlOp.algorithm">
                    <a-select-option value="rf">RandomForest</a-select-option>
                    <a-select-option value="xgb">XGBoost</a-select-option>
                    <a-select-option value="lgbm">LightGBM</a-select-option>
                    <a-select-option value="mlp">MLP</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="目标列">
                  <a-select v-model:value="mlOp.target_col" placeholder="选择目标列">
                    <a-select-option v-for="column in columns" :key="column" :value="column">
                      {{ column }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="特征列">
                  <a-select v-model:value="mlOp.feature_cols" mode="multiple" placeholder="留空则自动使用其余数值列">
                    <a-select-option v-for="column in numericColumns" :key="column" :value="column">
                      {{ column }}
                    </a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="测试集比例">
                  <a-slider
                    v-model:value="mlOp.test_size"
                    :min="0.1"
                    :max="0.5"
                    :step="0.05"
                    :tip-formatter="(value: number) => `${Math.round(value * 100)}%`"
                  />
                </a-form-item>
                <a-button type="primary" block @click="applyPredictiveModeling" :loading="processing">训练并评估</a-button>
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
              <div v-if="missingStats || outlierPreview">
                <a-row :gutter="16" class="mb-16">
                  <a-col :span="6">
                    <a-card size="small" title="异常值数量">
                      {{ outlierPreview?.outlier_count ?? '-' }}
                    </a-card>
                  </a-col>
                  <a-col :span="6">
                    <a-card size="small" title="下界">
                      {{ formatMetricValue(outlierPreview?.summary?.lower_bound) }}
                    </a-card>
                  </a-col>
                  <a-col :span="6">
                    <a-card size="small" title="上界">
                      {{ formatMetricValue(outlierPreview?.summary?.upper_bound) }}
                    </a-card>
                  </a-col>
                  <a-col :span="6">
                    <a-card size="small" title="均值 / 标准差">
                      {{ formatMetricValue(outlierPreview?.summary?.mean) }} / {{ formatMetricValue(outlierPreview?.summary?.std) }}
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
            </a-tab-pane>

            <a-tab-pane key="encoding" tab="编码预览">
              <a-card v-if="lastEncodingPreview" size="small" title="最近一次编码方案">
                <a-descriptions bordered :column="2" size="small">
                  <a-descriptions-item label="目标列">{{ lastEncodingPreview.column }}</a-descriptions-item>
                  <a-descriptions-item label="识别类型">{{ lastEncodingPreview.value_mode === 'multi_value' ? '多值列' : '单值列' }}</a-descriptions-item>
                  <a-descriptions-item label="推荐方案">{{ lastEncodingPreview.recommended_encoding }}</a-descriptions-item>
                  <a-descriptions-item label="唯一值数">{{ lastEncodingPreview.unique_count }}</a-descriptions-item>
                </a-descriptions>
                <a-table
                  class="mt-16"
                  :columns="encodingPreviewColumns"
                  :data-source="encodingPreviewRows"
                  :pagination="false"
                  size="small"
                  row-key="value"
                />
              </a-card>
              <a-empty v-else description="先在左侧打开编码预览弹窗" />
            </a-tab-pane>

            <a-tab-pane key="model_results" tab="建模结果">
              <a-space direction="vertical" style="width: 100%">
                <a-card
                  v-for="task in modelingTasks"
                  :key="task.id"
                  :title="task.name"
                  size="small"
                >
                  <a-descriptions bordered :column="3" size="small">
                    <a-descriptions-item label="状态">{{ task.status }}</a-descriptions-item>
                    <a-descriptions-item label="任务类型">{{ task.result?.kind }}</a-descriptions-item>
                    <a-descriptions-item label="完成时间">{{ formatDateTime(task.finished_at || task.created_at) }}</a-descriptions-item>
                  </a-descriptions>

                  <a-table
                    class="mt-16"
                    :columns="buildTaskMetricColumns(task)"
                    :data-source="buildTaskMetricRows(task)"
                    :pagination="false"
                    size="small"
                    row-key="metric"
                  />

                  <a-table
                    v-if="task.result?.feature_importance?.length"
                    class="mt-16"
                    :columns="featureImportanceColumns"
                    :data-source="task.result.feature_importance"
                    :pagination="false"
                    size="small"
                    row-key="feature"
                  />
                </a-card>
                <a-empty v-if="!modelingTasks.length" description="暂无聚类或建模结果" />
              </a-space>
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>
    </a-row>

    <a-modal
      v-model:open="encodingPreviewVisible"
      title="编码预览与确认"
      width="760px"
      :confirm-loading="processing"
      @ok="confirmEncoding"
    >
      <template v-if="encodingPreviewData">
        <a-descriptions bordered :column="2" size="small">
          <a-descriptions-item label="目标列">{{ encodingPreviewData.column }}</a-descriptions-item>
          <a-descriptions-item label="列类型">{{ encodingPreviewData.value_mode === 'multi_value' ? '多值列' : '单值列' }}</a-descriptions-item>
          <a-descriptions-item label="推荐方式">{{ encodingPreviewData.recommended_encoding }}</a-descriptions-item>
          <a-descriptions-item label="唯一值数">{{ encodingPreviewData.unique_count }}</a-descriptions-item>
        </a-descriptions>

        <a-form layout="vertical" class="mt-16">
          <a-form-item label="编码方式">
            <a-radio-group v-model:value="encodingSelectedMode">
              <a-radio v-for="option in encodingPreviewData.encoding_options" :key="option.key" :value="option.key">
                {{ option.label }}
              </a-radio>
            </a-radio-group>
          </a-form-item>
        </a-form>

        <a-table
          :columns="encodingPreviewColumns"
          :data-source="encodingPreviewRows"
          :pagination="false"
          size="small"
          row-key="value"
        />

        <a-table
          v-if="encodingSelectedMode === 'ordinal_encode'"
          class="mt-16"
          :columns="ordinalMappingColumns"
          :data-source="ordinalMappingRows"
          :pagination="false"
          size="small"
          row-key="value"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'encoded'">
              <a-input-number v-model:value="record.encoded" :min="1" style="width: 100%" />
            </template>
          </template>
        </a-table>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'

import Chart from '@/components/Chart.vue'
import DataPreviewTable from '@/components/DataPreviewTable.vue'
import request from '@/utils/request'
import { useTaskStore } from '@/store/modules/task'

const route = useRoute()
const taskStore = useTaskStore()

const projectId = computed(() => String(route.params.projectId || ''))

const datasets = ref<any[]>([])
const selectedDatasetId = ref<number | null>(null)
const currentDataset = ref<any | null>(null)
const columns = ref<string[]>([])
const tableColumns = ref<any[]>([])
const tableData = ref<any[]>([])
const tableLoading = ref(false)
const processing = ref(false)
const activeKey = ref(['cleaning'])
const activeTab = ref('data')

const pagination = ref({
  current: 1,
  pageSize: 50,
  total: 0,
  showSizeChanger: true
})

const missingStats = ref<any | null>(null)
const outlierPreview = ref<any | null>(null)
const outlierChartOptions = ref<any | null>(null)
const lastEncodingPreview = ref<any | null>(null)
const encodingPreviewVisible = ref(false)
const encodingPreviewData = ref<any | null>(null)
const encodingSelectedMode = ref('ordinal_encode')
const ordinalMappingRows = ref<any[]>([])

const quickCleanOp = ref({
  column: '',
  method: 'iqr',
  strategy: 'clip',
  z_threshold: 3
})

const transformOp = ref<any>({
  type: 'compute_column',
  new_column: '',
  expression: '',
  columns: [],
  method: 'minmax'
})

const encodeOp = ref({
  column: '',
  separator: ',',
  keep_original: true
})

const clusterOp = ref<any>({
  algorithm: 'kmeans',
  features: [],
  auto_k: true,
  k: 3,
  k_min: 2,
  k_max: 10,
  eps: 0.5,
  min_samples: 5,
  min_cluster_size: 5,
  bandwidth: undefined
})

const mlOp = ref<any>({
  task_type: 'classification',
  algorithm: 'rf',
  target_col: '',
  feature_cols: [],
  test_size: 0.2
})

const numericColumns = computed(() => {
  const schema = currentDataset.value?.schema_info || []
  return schema
    .filter((item: any) => {
      const type = String(item.type || '').toLowerCase()
      return ['int', 'float', 'double', 'decimal', 'long', 'short'].some((keyword) => type.includes(keyword))
    })
    .map((item: any) => item.name)
})

const missingStatsColumns = [
  { title: '列名', dataIndex: 'name', key: 'name' },
  { title: '缺失数', dataIndex: 'missing_count', key: 'missing_count' },
  { title: '总数', dataIndex: 'total_count', key: 'total_count' },
  {
    title: '缺失率',
    dataIndex: 'missing_rate',
    key: 'missing_rate',
    customRender: ({ text }: any) => `${((Number(text) || 0) * 100).toFixed(2)}%`
  }
]

const outlierSampleRows = computed(() => {
  const values = outlierPreview.value?.sample_values || []
  return values.map((value: number, index: number) => ({
    key: index,
    index: index + 1,
    value
  }))
})

const outlierSampleColumns = [
  { title: '序号', dataIndex: 'index', key: 'index', width: 80 },
  { title: '异常值样例', dataIndex: 'value', key: 'value' }
]

const encodingPreviewColumns = [
  { title: '值', dataIndex: 'value', key: 'value' },
  { title: '出现次数', dataIndex: 'count', key: 'count', width: 120 }
]

const ordinalMappingColumns = [
  { title: '原始值', dataIndex: 'value', key: 'value' },
  { title: '映射值', dataIndex: 'encoded', key: 'encoded', width: 160 }
]

const encodingPreviewRows = computed(() => {
  const topValues = encodingPreviewData.value?.top_values || []
  return topValues.map((item: any) => ({ value: item.value, count: item.count }))
})

const modelingTasks = computed(() => {
  if (!selectedDatasetId.value) return []
  return [...taskStore.tasks]
    .filter((task) => task.status === 'completed' && task.result?.dataset_id === selectedDatasetId.value)
    .filter((task) => ['clustering', 'predictive_modeling'].includes(task.result?.kind))
    .sort((a, b) => new Date(b.finished_at || b.created_at || 0).getTime() - new Date(a.finished_at || a.created_at || 0).getTime())
})

const featureImportanceColumns = [
  { title: '特征', dataIndex: 'feature', key: 'feature' },
  {
    title: '重要性',
    dataIndex: 'importance',
    key: 'importance',
    customRender: ({ text }: any) => formatMetricValue(text)
  }
]

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

const fetchTaskList = async () => {
  if (!projectId.value) return
  await taskStore.fetchTasks(projectId.value)
}

const updateColumnsList = () => {
  columns.value = currentDataset.value?.schema_info?.map((item: any) => item.name) || []
  tableColumns.value = columns.value.map((column) => ({
    title: column,
    dataIndex: column,
    key: column,
    width: 160
  }))
  if (!quickCleanOp.value.column || !numericColumns.value.includes(quickCleanOp.value.column)) {
    quickCleanOp.value.column = numericColumns.value[0] || ''
  }
  if (!encodeOp.value.column) {
    encodeOp.value.column = columns.value[0] || ''
  }
}

const handleDatasetChange = async () => {
  currentDataset.value = datasets.value.find((item) => item.id === selectedDatasetId.value) || null
  missingStats.value = null
  outlierPreview.value = null
  outlierChartOptions.value = null
  updateColumnsList()
  pagination.value.current = 1
  await fetchTableData()
  await fetchTaskList()
}

const fetchTableData = async () => {
  if (!selectedDatasetId.value) return
  tableLoading.value = true
  try {
    const res: any = await request.get(`/datasets/${selectedDatasetId.value}/data`, {
      params: { page: pagination.value.current, size: pagination.value.pageSize }
    })
    if (res.success) {
      tableData.value = res.data.items || []
      pagination.value.total = res.data.total || 0
    }
  } catch {
    message.error('获取表格数据失败')
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

const executeOperation = async (operation: any) => {
  if (!selectedDatasetId.value) return
  processing.value = true
  try {
    const res: any = await request.post(`/processing/${selectedDatasetId.value}/process`, [operation])
    if (res.success) {
      message.success('操作成功')
      await refreshCurrentDataset()
      await fetchTableData()
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '处理失败')
  } finally {
    processing.value = false
  }
}

const loadMissingStats = async () => {
  if (!selectedDatasetId.value) return
  processing.value = true
  try {
    const res: any = await request.get(`/quick-cleaning/${selectedDatasetId.value}/missing-stats`)
    if (res.success) {
      missingStats.value = res.data
      activeTab.value = 'cleaning'
      message.success('缺失值统计已加载')
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '获取缺失值统计失败')
  } finally {
    processing.value = false
  }
}

const previewOutliers = async () => {
  if (!selectedDatasetId.value || !quickCleanOp.value.column) {
    message.warning('请选择异常值目标列')
    return
  }
  processing.value = true
  try {
    const res: any = await request.post(`/quick-cleaning/${selectedDatasetId.value}/outlier-preview`, {
      column: quickCleanOp.value.column,
      method: quickCleanOp.value.method,
      z_threshold: quickCleanOp.value.z_threshold
    })
    if (res.success) {
      outlierPreview.value = res.data
      outlierChartOptions.value = {
        tooltip: { trigger: 'axis' },
        xAxis: { type: 'category', data: outlierSampleRows.value.map((item: any) => `样例${item.index}`) },
        yAxis: { type: 'value' },
        series: [
          {
            type: 'bar',
            data: outlierSampleRows.value.map((item: any) => item.value),
            itemStyle: { color: '#f59f00', borderRadius: [8, 8, 0, 0] }
          }
        ]
      }
      activeTab.value = 'cleaning'
      message.success('异常值预览已更新')
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '异常值预览失败')
  } finally {
    processing.value = false
  }
}

const applyQuickOutlierHandling = async () => {
  if (!selectedDatasetId.value || !quickCleanOp.value.column) {
    message.warning('请选择异常值目标列')
    return
  }
  processing.value = true
  try {
    const res: any = await request.post(`/quick-cleaning/${selectedDatasetId.value}/outlier-handle`, {
      column: quickCleanOp.value.column,
      method: quickCleanOp.value.method,
      strategy: quickCleanOp.value.strategy,
      z_threshold: quickCleanOp.value.z_threshold
    })
    if (res.success) {
      message.success(`异常值处理完成，影响 ${res.data.affected_rows} 行`)
      await refreshCurrentDataset()
      await fetchTableData()
      await loadMissingStats()
      await previewOutliers()
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '异常值处理失败')
  } finally {
    processing.value = false
  }
}

const applyTransformOp = async () => {
  const op = { type: transformOp.value.type, params: { ...transformOp.value } }
  await executeOperation(op)
}

const previewEncoding = async () => {
  if (!selectedDatasetId.value || !encodeOp.value.column) {
    message.warning('请选择需要编码的列')
    return
  }
  processing.value = true
  try {
    const res: any = await request.post(`/processing/${selectedDatasetId.value}/encoding-preview`, {
      column: encodeOp.value.column,
      separator: encodeOp.value.separator
    })
    if (res.success) {
      encodingPreviewData.value = res.data
      encodingSelectedMode.value = res.data.recommended_encoding
      ordinalMappingRows.value = Object.entries(res.data.recommended_mapping || {}).map(([value, encoded]) => ({
        value,
        encoded
      }))
      encodingPreviewVisible.value = true
      lastEncodingPreview.value = res.data
      activeTab.value = 'encoding'
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '生成编码预览失败')
  } finally {
    processing.value = false
  }
}

const confirmEncoding = async () => {
  if (!encodingPreviewData.value) return
  const column = encodingPreviewData.value.column
  let operation: any

  if (encodingSelectedMode.value === 'ordinal_encode') {
    const mapping = Object.fromEntries(ordinalMappingRows.value.map((item) => [item.value, Number(item.encoded)]))
    operation = {
      type: 'ordinal_encode',
      params: {
        column,
        keep_original: encodeOp.value.keep_original,
        mapping,
        encoded_column: `${column}_编码`
      }
    }
  } else if (encodingSelectedMode.value === 'multi_hot_encode') {
    operation = {
      type: 'multi_hot_encode',
      params: {
        column,
        separator: encodeOp.value.separator,
        keep_original: encodeOp.value.keep_original
      }
    }
  } else {
    operation = {
      type: 'one_hot_encode',
      params: {
        columns: [column],
        keep_original: encodeOp.value.keep_original
      }
    }
  }

  encodingPreviewVisible.value = false
  await executeOperation(operation)
  message.success('编码处理完成')
}

const applyClustering = async () => {
  if (!selectedDatasetId.value || clusterOp.value.features.length === 0) {
    message.warning('请选择聚类特征列')
    return
  }
  processing.value = true
  try {
    const payload = {
      features: clusterOp.value.features,
      algorithm: clusterOp.value.algorithm,
      n_clusters: clusterOp.value.auto_k ? 0 : clusterOp.value.k,
      k_min: clusterOp.value.k_min,
      k_max: clusterOp.value.k_max,
      eps: clusterOp.value.eps,
      min_samples: clusterOp.value.min_samples,
      min_cluster_size: clusterOp.value.min_cluster_size,
      bandwidth: clusterOp.value.bandwidth
    }
    const res: any = await request.post(`/modeling/${selectedDatasetId.value}/clustering`, payload)
    if (res.success) {
      await fetchTaskList()
      activeTab.value = 'model_results'
      message.success('聚类任务已提交')
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '聚类任务提交失败')
  } finally {
    processing.value = false
  }
}

const applyPredictiveModeling = async () => {
  if (!selectedDatasetId.value || !mlOp.value.target_col) {
    message.warning('请选择目标列')
    return
  }
  const fallbackFeatures = numericColumns.value.filter((column: string) => column !== mlOp.value.target_col)
  const features = mlOp.value.feature_cols.length ? mlOp.value.feature_cols : fallbackFeatures
  if (!features.length) {
    message.warning('当前没有可用的数值特征列')
    return
  }
  processing.value = true
  try {
    const res: any = await request.post(`/modeling/${selectedDatasetId.value}/predictive`, {
      target: mlOp.value.target_col,
      features,
      task_type: mlOp.value.task_type,
      algorithm: mlOp.value.algorithm,
      test_size: mlOp.value.test_size
    })
    if (res.success) {
      await fetchTaskList()
      activeTab.value = 'model_results'
      message.success('建模任务已提交')
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '建模任务提交失败')
  } finally {
    processing.value = false
  }
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
    message.success(`${payload.status === 'completed' ? '任务已完成' : '任务状态已更新'}：${payload.task_id}`)
  } catch (error) {
    console.error('Processing task parse failed', error)
  }
}

const buildTaskMetricRows = (task: any) => {
  const metrics = task.result?.metrics || {}
  return Object.keys(metrics).map((key) => ({
    metric: key,
    value: formatMetricValue(metrics[key])
  }))
}

const buildTaskMetricColumns = (_task: any) => ([
  { title: '指标', dataIndex: 'metric', key: 'metric' },
  { title: '结果', dataIndex: 'value', key: 'value' }
])

const formatMetricValue = (value: any) => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(4) : value ?? '-'
}

const formatDateTime = (value: string) => {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-'
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

.mt-16 {
  margin-top: 16px;
}

.mb-16 {
  margin-bottom: 16px;
}

.split-action-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
  width: 100%;
}
</style>
