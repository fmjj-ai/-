<template>
  <div class="sentiment-container">
    <a-row :gutter="24" class="full-height">
      <a-col :span="8" class="full-height">
        <a-card title="情感分析与 NLP" :bordered="false" class="neumorphism-card full-height panel-scroll">
          <a-form layout="vertical">
            <DatasetSelector
              v-model="selectedDatasetId"
              :datasets="datasets"
              @change="onDatasetChange"
            />

            <SentimentConfigForm
              v-if="selectedDatasetId"
              :config="config"
              :columns="columns"
              v-model:custom-stopwords="customStopwords"
              :mask-artifact="latestMaskArtifact"
              :submitting="submitting"
              :palette-options="paletteOptions"
              :wordcloud-scope-options="wordcloudScopeOptions"
              :build-artifact-preview-url="buildArtifactPreviewUrl"
              @upload-mask="uploadMaskImage"
              @clear-mask="clearMaskArtifact"
              @start-analysis="startAnalysis"
              @reload-results="loadAnalysisResults({ forceDataReload: true })"
            />
          </a-form>
        </a-card>
      </a-col>

      <a-col :span="16" class="full-height">
        <a-card title="结果展示" :bordered="false" class="neumorphism-card full-height panel-scroll">
          <template #extra>
            <a-space v-if="latestSentimentTask">
              <span class="result-meta">最近任务：{{ latestSentimentTask.name }}</span>
              <span class="result-meta">
                {{ formatDateTime(latestSentimentTask.finished_at || latestSentimentTask.created_at) }}
              </span>
            </a-space>
          </template>

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

            <a-tab-pane key="distribution" tab="情感分布">
              <DistributionTab :rows="distributionRows" />
            </a-tab-pane>

            <a-tab-pane key="wordcloud" tab="词云预览">
              <WordcloudTab
                :artifacts="wordcloudArtifacts"
                :build-artifact-preview-url="buildArtifactPreviewUrl"
              />
            </a-tab-pane>

            <a-tab-pane key="tfidf" tab="TF-IDF 关键词">
              <TfidfTab :rows="tfidfRows" />
            </a-tab-pane>

            <a-tab-pane key="lda" tab="LDA 主题">
              <LdaTab
                :rows="ldaRows"
                :latest-lda-result="latestLdaResult"
                :lda-vis-artifact="ldaVisArtifact"
                @open-artifact="openArtifactPreview"
              />
            </a-tab-pane>

            <a-tab-pane key="messages" tab="运行信息">
              <MessagesTab :warnings="taskWarnings" :second-pass-summary="secondPassSummary" />
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'

import DatasetSelector from '@/components/common/DatasetSelector.vue'
import DataPreviewTable from '@/components/DataPreviewTable.vue'
import SentimentConfigForm from '@/components/sentiment/SentimentConfigForm.vue'
import DistributionTab from '@/components/sentiment/DistributionTab.vue'
import WordcloudTab from '@/components/sentiment/WordcloudTab.vue'
import TfidfTab from '@/components/sentiment/TfidfTab.vue'
import LdaTab from '@/components/sentiment/LdaTab.vue'
import MessagesTab from '@/components/sentiment/MessagesTab.vue'

import request from '@/utils/request'
import { useTaskStore } from '@/store/modules/task'
import { useAsyncAction } from '@/composables/useAsyncAction'
import { useDatasets } from '@/composables/useDatasets'

const route = useRoute()
const taskStore = useTaskStore()

const projectId = computed(() => String(route.params.projectId || ''))
const apiBaseUrl = computed(() => import.meta.env.VITE_API_BASE_URL || '/api/v1')

const { showError } = useAsyncAction()

const {
  datasets,
  selectedDatasetId,
  columns,
  fetchDatasets,
  handleChange,
} = useDatasets(() => projectId.value, {
  onChange: async () => {
    pagination.value.current = 1
    await loadDatasetData(1, pagination.value.pageSize)
    await loadAnalysisResults({ skipDataReload: true })
  },
})

const tableColumns = ref<any[]>([])
const tableData = ref<any[]>([])
const tableLoading = ref(false)
const submitting = ref(false)
const activeTab = ref('distribution')
const latestTaskArtifacts = ref<any[]>([])
const latestMaskArtifact = ref<any | null>(null)
const lastSubmittedTaskId = ref<string | null>(null)
const customStopwords = ref('')

const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true,
})

const paletteOptions = [
  { value: 'viridis', label: '青绿渐变', colors: ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'] },
  { value: 'plasma', label: '玫紫暖光', colors: ['#0d0887', '#7e03a8', '#cc4778', '#f89441', '#f0f921'] },
  { value: 'magma', label: '岩浆棕红', colors: ['#000004', '#51127c', '#b63679', '#fb8861', '#fcfdbf'] },
  { value: 'coolwarm', label: '冷暖对照', colors: ['#3b4cc0', '#8db0fe', '#dddcdc', '#f4987a', '#b40426'] },
]
const wordcloudScopeOptions = [
  { label: '正向', value: 'positive' },
  { label: '负向', value: 'negative' },
  { label: '总体', value: 'overall' },
]

const config = reactive({
  text_column: '',
  method: 'snownlp' as 'snownlp' | 'deepseek',
  api_key: '',
  base_url: 'https://api.deepseek.com/v1',
  model_name: 'deepseek-chat',
  enable_second_pass_snownlp: true,
  pseudo_label_positive_threshold: 0.9,
  pseudo_label_negative_threshold: 0.1,
  stopwords: [] as string[],
  extract_tfidf: true,
  top_k: 20,
  export_tfidf_table: true,
  run_lda: false,
  lda_min_k: 2,
  lda_max_k: 10,
  lda_k: 5,
  generate_lda_vis: false,
  export_lda_table: true,
  generate_wordcloud: true,
  wordcloud_scopes: ['positive', 'negative', 'overall'] as string[],
  wordcloud_max_words: 120,
  wordcloud_palette_key: 'viridis',
  wordcloud_mask_artifact_id: null as number | null,
  wc_font: 'Microsoft YaHei',
  wc_contour: false,
})

const latestSentimentTask = computed(() => {
  if (!selectedDatasetId.value) return null
  return (
    [...taskStore.tasks]
      .filter(
        (task) =>
          task.status === 'completed' &&
          task.result?.kind === 'sentiment_analysis' &&
          task.result?.dataset_id === selectedDatasetId.value
      )
      .sort(
        (a, b) =>
          new Date(b.finished_at || b.created_at || 0).getTime() -
          new Date(a.finished_at || a.created_at || 0).getTime()
      )[0] || null
  )
})

const latestTaskResult = computed(() => latestSentimentTask.value?.result || null)
const distributionRows = computed(() =>
  (latestTaskResult.value?.sentiment_distribution || []).map((item: any) => ({
    ...item,
    key: item.label,
  }))
)
const tfidfRows = computed(() =>
  (latestTaskResult.value?.tfidf || []).map((item: any) => ({ ...item, key: item.word }))
)
const latestLdaResult = computed(() => latestTaskResult.value?.lda || null)
const ldaRows = computed(() => {
  const topics = latestLdaResult.value?.topics || []
  return topics.flatMap((topic: any) =>
    (topic.keywords || []).map((keyword: string, index: number) => ({
      key: `${topic.topic}-${keyword}-${index}`,
      topic: topic.topic,
      rank: index + 1,
      keyword,
    }))
  )
})
const taskWarnings = computed(() => latestTaskResult.value?.warnings || [])
const secondPassSummary = computed(() => latestTaskResult.value?.second_pass || null)
const wordcloudArtifacts = computed(() =>
  latestTaskArtifacts.value.filter((artifact) => artifact.type === 'png' && artifact.name.includes('词云'))
)
const ldaVisArtifact = computed(
  () =>
    latestTaskArtifacts.value.find(
      (artifact) => artifact.type === 'html' && artifact.name.includes('LDA可视化')
    ) || null
)

const applyMaskArtifact = (artifact: any | null) => {
  latestMaskArtifact.value = artifact
  config.wordcloud_mask_artifact_id = artifact?.id ?? null
}

const syncPreviewColumns = (payload: any) => {
  const names: string[] = payload.columns || []
  tableColumns.value = names.map((column) => ({
    title: column,
    dataIndex: column,
    key: column,
    width: 160,
    ellipsis: true,
  }))
  if (!config.text_column && names.length) {
    config.text_column = names[0]
  }
}

const buildStopwords = () =>
  customStopwords.value
    .split(/[\r\n,]+/)
    .map((item) => item.trim())
    .filter(Boolean)

const validateAnalysisConfig = () => {
  if (!selectedDatasetId.value) return '请先选择数据集'
  if (!config.text_column) return '请选择文本列'
  if (config.method === 'deepseek' && !config.api_key.trim())
    return '使用自定义 LLM API 时请填写 API Key'
  if (config.run_lda && config.lda_max_k <= config.lda_min_k)
    return 'LDA 最大主题数必须大于最小主题数'
  if (config.generate_wordcloud && config.wordcloud_scopes.length === 0)
    return '请至少选择一个词云范围'
  return ''
}

const fetchTaskList = async () => {
  if (!projectId.value) return
  await taskStore.fetchTasks(projectId.value)
}

const loadDatasetData = async (page: number, pageSize: number) => {
  if (!selectedDatasetId.value) return
  tableLoading.value = true
  try {
    const res: any = await request.get(`/datasets/${selectedDatasetId.value}/data`, {
      params: { page, size: pageSize },
    })
    if (res.success) {
      const payload = res.data || {}
      tableData.value = payload.items || []
      pagination.value.current = page
      pagination.value.pageSize = pageSize
      pagination.value.total = payload.total || 0
      syncPreviewColumns(payload)
    }
  } catch (error: any) {
    showError(error, '获取数据预览失败')
  } finally {
    tableLoading.value = false
  }
}

const fetchArtifactsForTask = async (taskId?: string | null) => {
  if (!taskId) {
    latestTaskArtifacts.value = []
    return
  }
  try {
    const res: any = await request.get('/artifacts/', {
      params: { project_id: Number(projectId.value), task_id: taskId, limit: 50 },
    })
    if (res.success) {
      latestTaskArtifacts.value = res.data || []
    }
  } catch {
    latestTaskArtifacts.value = []
  }
}

const loadLatestMaskArtifact = async () => {
  try {
    const res: any = await request.get('/artifacts/', {
      params: {
        project_id: Number(projectId.value),
        type: 'png',
        name_prefix: '词云轮廓图_',
        limit: 1,
      },
    })
    if (res.success && Array.isArray(res.data) && res.data.length > 0) {
      applyMaskArtifact(res.data[0])
    } else {
      applyMaskArtifact(null)
    }
  } catch {
    applyMaskArtifact(null)
  }
}

const onDatasetChange = async () => {
  await handleChange()
}

const handleTableChange = (pageInfo: any) => {
  loadDatasetData(pageInfo.current, pageInfo.pageSize)
}

const buildArtifactPreviewUrl = (artifactId: number) =>
  `${apiBaseUrl.value}/artifacts/${artifactId}/preview`

const openArtifactPreview = (artifactId: number) => {
  window.open(buildArtifactPreviewUrl(artifactId), '_blank', 'noopener')
}

const clearMaskArtifact = () => {
  applyMaskArtifact(null)
  config.wc_contour = false
}

const uploadMaskImage = async (options: any) => {
  const formData = new FormData()
  formData.append('project_id', projectId.value)
  formData.append('name', `词云轮廓图_${dayjs().format('YYYYMMDD_HHmmss')}`)
  formData.append('file', options.file)

  try {
    const res: any = await request.post('/artifacts/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    if (res.success) {
      applyMaskArtifact(res.data)
      message.success('轮廓图上传成功')
      options.onSuccess?.(res)
    } else {
      options.onError?.(new Error('上传失败'))
    }
  } catch (error) {
    showError(error, '轮廓图上传失败')
    options.onError?.(error)
  }
}

const startAnalysis = async () => {
  const validationMessage = validateAnalysisConfig()
  if (validationMessage) {
    message.warning(validationMessage)
    return
  }

  submitting.value = true
  try {
    const payload = { ...config, stopwords: buildStopwords() }
    const res: any = await request.post(
      `/sentiment/${selectedDatasetId.value}/analyze`,
      payload
    )
    if (res.success) {
      lastSubmittedTaskId.value = res.data
      await fetchTaskList()
      message.success('情感分析任务已提交，请在任务中心查看进度')
    }
  } catch (error: any) {
    showError(error, '提交情感分析任务失败')
  } finally {
    submitting.value = false
  }
}

const resolveAnalysisTaskId = () => lastSubmittedTaskId.value || latestSentimentTask.value?.id

const loadAnalysisResults = async (options?: {
  skipDataReload?: boolean
  forceDataReload?: boolean
}) => {
  if (!selectedDatasetId.value) return
  if (options?.forceDataReload || !options?.skipDataReload) {
    await loadDatasetData(pagination.value.current, pagination.value.pageSize)
  }
  await fetchTaskList()
  const targetTaskId = resolveAnalysisTaskId()
  await fetchArtifactsForTask(targetTaskId)
}

const handleTaskUpdate = async (event: MessageEvent) => {
  if (event.data === 'ping' || !selectedDatasetId.value) return
  try {
    const payload = JSON.parse(event.data)
    const result = payload.result || {}
    if (payload.status !== 'completed') return
    if (result.kind !== 'sentiment_analysis' || result.dataset_id !== selectedDatasetId.value) return

    lastSubmittedTaskId.value = payload.task_id
    await fetchTaskList()
    await loadAnalysisResults({ forceDataReload: true })
    message.success('情感分析结果已自动刷新')
  } catch (error) {
    console.error('Sentiment task stream parse failed', error)
  }
}

const formatDateTime = (value: string) =>
  value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-'

onMounted(async () => {
  await fetchDatasets()
  await fetchTaskList()
  await loadLatestMaskArtifact()
  taskStore.connectSSE()
  taskStore.eventSource?.addEventListener('message', handleTaskUpdate)
})

onBeforeUnmount(() => {
  taskStore.eventSource?.removeEventListener('message', handleTaskUpdate)
})
</script>

<style scoped>
.sentiment-container {
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

.result-meta {
  color: var(--text-secondary);
  font-size: 12px;
}
</style>
