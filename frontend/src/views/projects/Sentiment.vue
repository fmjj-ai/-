<template>
  <div class="sentiment-container">
    <a-row :gutter="24" class="full-height">
      <a-col :span="8" class="full-height">
        <a-card title="情感分析与 NLP" :bordered="false" class="neumorphism-card full-height panel-scroll">
          <a-form layout="vertical">
            <a-form-item label="选择数据集">
              <a-select v-model:value="selectedDatasetId" placeholder="请选择数据集" @change="handleDatasetChange">
                <a-select-option v-for="dataset in datasets" :key="dataset.id" :value="dataset.id">
                  {{ dataset.name }}
                </a-select-option>
              </a-select>
            </a-form-item>

            <template v-if="selectedDatasetId">
              <a-form-item label="文本列选择">
                <a-select v-model:value="config.text_column" placeholder="选择包含文本内容的列">
                  <a-select-option v-for="column in columns" :key="column" :value="column">
                    {{ column }}
                  </a-select-option>
                </a-select>
              </a-form-item>

              <a-form-item label="分析模型">
                <a-select v-model:value="config.method">
                  <a-select-option value="snownlp">SnowNLP（本地内置）</a-select-option>
                  <a-select-option value="deepseek">自定义 LLM API</a-select-option>
                </a-select>
              </a-form-item>

              <template v-if="config.method === 'deepseek'">
                <a-form-item label="API Key">
                  <a-input-password v-model:value="config.api_key" placeholder="sk-..." allow-clear />
                </a-form-item>
                <a-form-item label="Base URL">
                  <a-input v-model:value="config.base_url" allow-clear />
                </a-form-item>
                <a-form-item label="模型名称">
                  <a-input v-model:value="config.model_name" placeholder="例如 deepseek-chat" allow-clear />
                </a-form-item>
              </template>

              <template v-else>
                <a-divider orientation="left">二次 SnowNLP</a-divider>
                <a-form-item>
                  <a-checkbox v-model:checked="config.enable_second_pass_snownlp">
                    启用高置信度伪标签二次训练
                  </a-checkbox>
                </a-form-item>
                <a-row :gutter="12">
                  <a-col :span="12">
                    <a-form-item label="正向阈值">
                      <a-input-number v-model:value="config.pseudo_label_positive_threshold" :min="0.5" :max="1" :step="0.05" style="width: 100%" />
                    </a-form-item>
                  </a-col>
                  <a-col :span="12">
                    <a-form-item label="负向阈值">
                      <a-input-number v-model:value="config.pseudo_label_negative_threshold" :min="0" :max="0.5" :step="0.05" style="width: 100%" />
                    </a-form-item>
                  </a-col>
                </a-row>
              </template>

              <a-form-item label="自定义停用词（逗号或换行分隔）">
                <a-textarea v-model:value="customStopwords" :rows="3" placeholder="例如：的,了,还是,然后" />
              </a-form-item>

              <a-divider orientation="left">关键词与主题</a-divider>
              <a-form-item>
                <a-checkbox v-model:checked="config.extract_tfidf">提取 TF-IDF 关键词</a-checkbox>
              </a-form-item>
              <a-row :gutter="12">
                <a-col :span="12">
                  <a-form-item label="TF-IDF Top K">
                    <a-input-number v-model:value="config.top_k" :min="5" :max="100" style="width: 100%" />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item>
                    <a-checkbox v-model:checked="config.export_tfidf_table">导出 TF-IDF 表格</a-checkbox>
                  </a-form-item>
                </a-col>
              </a-row>

              <a-form-item>
                <a-checkbox v-model:checked="config.run_lda">执行 LDA 主题提取</a-checkbox>
              </a-form-item>
              <template v-if="config.run_lda">
                <a-row :gutter="12">
                  <a-col :span="8">
                    <a-form-item label="最小主题数">
                      <a-input-number v-model:value="config.lda_min_k" :min="2" :max="20" style="width: 100%" />
                    </a-form-item>
                  </a-col>
                  <a-col :span="8">
                    <a-form-item label="最大主题数">
                      <a-input-number v-model:value="config.lda_max_k" :min="3" :max="30" style="width: 100%" />
                    </a-form-item>
                  </a-col>
                  <a-col :span="8">
                    <a-form-item label="最终 K">
                      <a-input-number v-model:value="config.lda_k" :min="2" :max="20" style="width: 100%" />
                    </a-form-item>
                  </a-col>
                </a-row>
                <a-space direction="vertical" style="width: 100%">
                  <a-checkbox v-model:checked="config.generate_lda_vis">生成 LDA 交互可视化</a-checkbox>
                  <a-checkbox v-model:checked="config.export_lda_table">导出 LDA 结果表</a-checkbox>
                </a-space>
              </template>

              <a-divider orientation="left">词云配置</a-divider>
              <a-form-item>
                <a-checkbox v-model:checked="config.generate_wordcloud">生成词云图</a-checkbox>
              </a-form-item>
              <template v-if="config.generate_wordcloud">
                <a-form-item label="词云范围">
                  <a-checkbox-group v-model:value="config.wordcloud_scopes" :options="wordcloudScopeOptions" />
                </a-form-item>
                <a-row :gutter="12">
                  <a-col :span="12">
                    <a-form-item label="词数上限">
                      <a-input-number v-model:value="config.wordcloud_max_words" :min="20" :max="300" style="width: 100%" />
                    </a-form-item>
                  </a-col>
                  <a-col :span="12">
                    <a-form-item label="字体">
                      <a-select v-model:value="config.wc_font">
                        <a-select-option value="Microsoft YaHei">微软雅黑</a-select-option>
                        <a-select-option value="SimHei">黑体</a-select-option>
                        <a-select-option value="SimSun">宋体</a-select-option>
                      </a-select>
                    </a-form-item>
                  </a-col>
                </a-row>

                <a-form-item label="色卡方案">
                  <a-select v-model:value="config.wordcloud_palette_key">
                    <a-select-option v-for="palette in paletteOptions" :key="palette.value" :value="palette.value">
                      {{ palette.label }}
                    </a-select-option>
                  </a-select>
                  <div class="palette-preview">
                    <div class="palette-label">当前颜色示意</div>
                    <div class="palette-swatches">
                      <span
                        v-for="color in selectedPalette.colors"
                        :key="color"
                        class="palette-chip"
                        :style="{ backgroundColor: color }"
                      ></span>
                    </div>
                  </div>
                </a-form-item>

                <a-form-item label="词云轮廓图">
                  <a-space direction="vertical" style="width: 100%">
                    <a-upload :show-upload-list="false" :custom-request="uploadMaskImage" accept=".png,.jpg,.jpeg,.webp">
                      <a-button block>上传轮廓图</a-button>
                    </a-upload>
                    <a-checkbox v-model:checked="config.wc_contour" :disabled="!latestMaskArtifact">
                      使用轮廓描边
                    </a-checkbox>
                    <div v-if="latestMaskArtifact" class="mask-preview">
                      <img :src="buildArtifactPreviewUrl(latestMaskArtifact.id)" alt="mask" />
                      <div class="mask-meta">
                        <div>{{ latestMaskArtifact.name }}</div>
                        <a-button type="link" size="small" @click="clearMaskArtifact">清除轮廓</a-button>
                      </div>
                    </div>
                    <a-empty v-else :image="false" description="当前项目还没有上传轮廓图" />
                  </a-space>
                </a-form-item>
              </template>

              <a-space direction="vertical" style="width: 100%">
                <a-button type="primary" block :loading="submitting" @click="startAnalysis">开始分析</a-button>
                <a-button block @click="loadAnalysisResults({ forceDataReload: true })">刷新结果</a-button>
              </a-space>
            </template>
          </a-form>
        </a-card>
      </a-col>

      <a-col :span="16" class="full-height">
        <a-card title="结果展示" :bordered="false" class="neumorphism-card full-height panel-scroll">
          <template #extra>
            <a-space v-if="latestSentimentTask">
              <span class="result-meta">最近任务：{{ latestSentimentTask.name }}</span>
              <span class="result-meta">{{ formatDateTime(latestSentimentTask.finished_at || latestSentimentTask.created_at) }}</span>
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
              <div v-if="distributionRows.length" class="chart-shell">
                <Chart :options="sentimentChartOptions" height="420px" />
                <a-table
                  class="mt-16"
                  :columns="distributionColumns"
                  :data-source="distributionRows"
                  :pagination="false"
                  size="small"
                  row-key="label"
                />
              </div>
              <a-empty v-else description="暂无情感分布结果，请先执行分析" />
            </a-tab-pane>

            <a-tab-pane key="wordcloud" tab="词云预览">
              <div v-if="wordcloudArtifacts.length" class="wordcloud-grid">
                <a-card v-for="artifact in wordcloudArtifacts" :key="artifact.id" :title="artifact.name" size="small">
                  <img :src="buildArtifactPreviewUrl(artifact.id)" :alt="artifact.name" class="wordcloud-image" />
                </a-card>
              </div>
              <a-empty v-else description="暂无词云产物" />
            </a-tab-pane>

            <a-tab-pane key="tfidf" tab="TF-IDF 关键词">
              <a-table
                v-if="tfidfRows.length"
                :columns="tfidfColumns"
                :data-source="tfidfRows"
                :pagination="false"
                size="small"
                row-key="word"
              />
              <a-empty v-else description="暂无 TF-IDF 结果" />
            </a-tab-pane>

            <a-tab-pane key="lda" tab="LDA 主题">
              <template v-if="ldaRows.length">
                <a-space class="mb-16">
                  <a-tag color="blue">主题数 {{ latestLdaResult?.n_topics || 0 }}</a-tag>
                  <a-tag color="purple">困惑度 {{ formatMetric(latestLdaResult?.perplexity) }}</a-tag>
                  <a-button v-if="ldaVisArtifact" type="link" @click="openArtifactPreview(ldaVisArtifact.id)">打开 LDA 可视化</a-button>
                </a-space>
                <a-table :columns="ldaColumns" :data-source="ldaRows" :pagination="false" size="small" row-key="key" />
              </template>
              <a-empty v-else description="暂无 LDA 结果" />
            </a-tab-pane>

            <a-tab-pane key="messages" tab="运行信息">
              <a-alert
                v-if="secondPassSummary"
                type="info"
                show-icon
                class="mb-16"
                :message="buildSecondPassMessage(secondPassSummary)"
              />
              <a-alert
                v-for="warning in taskWarnings"
                :key="warning"
                type="warning"
                show-icon
                class="mb-12"
                :message="warning"
              />
              <a-empty v-if="!taskWarnings.length && !secondPassSummary" description="当前没有额外提示" />
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>
    </a-row>
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
const apiBaseUrl = computed(() => import.meta.env.VITE_API_BASE_URL || '/api/v1')

const datasets = ref<any[]>([])
const selectedDatasetId = ref<number | null>(null)
const columns = ref<string[]>([])
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
  showSizeChanger: true
})

const paletteOptions = [
  { value: 'viridis', label: '青绿渐变', colors: ['#440154', '#3b528b', '#21918c', '#5ec962', '#fde725'] },
  { value: 'plasma', label: '玫紫暖光', colors: ['#0d0887', '#7e03a8', '#cc4778', '#f89441', '#f0f921'] },
  { value: 'magma', label: '岩浆棕红', colors: ['#000004', '#51127c', '#b63679', '#fb8861', '#fcfdbf'] },
  { value: 'coolwarm', label: '冷暖对照', colors: ['#3b4cc0', '#8db0fe', '#dddcdc', '#f4987a', '#b40426'] }
]
const wordcloudScopeOptions = [
  { label: '正向', value: 'positive' },
  { label: '负向', value: 'negative' },
  { label: '总体', value: 'overall' }
]

const config = ref({
  text_column: '',
  method: 'snownlp',
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
  wc_contour: false
})

const selectedPalette = computed(() => {
  return paletteOptions.find((item) => item.value === config.value.wordcloud_palette_key) || paletteOptions[0]
})

const latestSentimentTask = computed(() => {
  if (!selectedDatasetId.value) return null
  return [...taskStore.tasks]
    .filter((task) => task.status === 'completed' && task.result?.kind === 'sentiment_analysis' && task.result?.dataset_id === selectedDatasetId.value)
    .sort((a, b) => new Date(b.finished_at || b.created_at || 0).getTime() - new Date(a.finished_at || a.created_at || 0).getTime())[0] || null
})

const latestTaskResult = computed(() => latestSentimentTask.value?.result || null)
const distributionRows = computed(() => (latestTaskResult.value?.sentiment_distribution || []).map((item: any) => ({
  ...item,
  key: item.label
})))
const tfidfRows = computed(() => (latestTaskResult.value?.tfidf || []).map((item: any) => ({ ...item, key: item.word })))
const latestLdaResult = computed(() => latestTaskResult.value?.lda || null)
const ldaRows = computed(() => {
  const topics = latestLdaResult.value?.topics || []
  return topics.flatMap((topic: any) =>
    (topic.keywords || []).map((keyword: string, index: number) => ({
      key: `${topic.topic}-${keyword}-${index}`,
      topic: topic.topic,
      rank: index + 1,
      keyword
    }))
  )
})
const taskWarnings = computed(() => latestTaskResult.value?.warnings || [])
const secondPassSummary = computed(() => latestTaskResult.value?.second_pass || null)
const wordcloudArtifacts = computed(() => latestTaskArtifacts.value.filter((artifact) => artifact.type === 'png' && artifact.name.includes('词云')))
const ldaVisArtifact = computed(() => latestTaskArtifacts.value.find((artifact) => artifact.type === 'html' && artifact.name.includes('LDA可视化')) || null)

const distributionColumns = [
  { title: '情感类型', dataIndex: 'label', key: 'label' },
  { title: '数量', dataIndex: 'count', key: 'count' },
  {
    title: '占比',
    dataIndex: 'ratio',
    key: 'ratio',
    customRender: ({ text }: any) => `${((Number(text) || 0) * 100).toFixed(2)}%`
  }
]
const tfidfColumns = [
  { title: '关键词', dataIndex: 'word', key: 'word' },
  {
    title: '得分',
    dataIndex: 'score',
    key: 'score',
    customRender: ({ text }: any) => formatMetric(text)
  }
]
const ldaColumns = [
  { title: '主题', dataIndex: 'topic', key: 'topic', width: 100 },
  { title: '关键词序号', dataIndex: 'rank', key: 'rank', width: 120 },
  { title: '关键词', dataIndex: 'keyword', key: 'keyword' }
]

const sentimentChartOptions = computed(() => ({
  tooltip: {
    trigger: 'item',
    formatter: ({ data }: any) => `${data.name}<br/>数量：${data.value}<br/>占比：${((data.ratio || 0) * 100).toFixed(2)}%`
  },
  legend: { orient: 'vertical', left: 'left' },
  series: [
    {
      name: '情感分布',
      type: 'pie',
      radius: ['40%', '70%'],
      label: {
        formatter: ({ data }: any) => `${data.name}: ${data.value} (${((data.ratio || 0) * 100).toFixed(1)}%)`
      },
      data: distributionRows.value.map((item: any) => ({
        name: item.label,
        value: item.count,
        ratio: item.ratio
      }))
    }
  ]
}))

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

const loadDatasetData = async (page: number, pageSize: number) => {
  if (!selectedDatasetId.value) return
  tableLoading.value = true
  try {
    const res: any = await request.get(`/datasets/${selectedDatasetId.value}/data`, {
      params: { page, size: pageSize }
    })
    if (res.success) {
      const payload = res.data || {}
      tableData.value = payload.items || []
      pagination.value.current = page
      pagination.value.pageSize = pageSize
      pagination.value.total = payload.total || 0
      columns.value = payload.columns || []
      tableColumns.value = columns.value.map((column) => ({
        title: column,
        dataIndex: column,
        key: column,
        width: 160,
        ellipsis: true
      }))
      if (!config.value.text_column && columns.value.length) {
        config.value.text_column = columns.value[0]
      }
    }
  } catch {
    message.error('获取数据预览失败')
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
      params: { project_id: Number(projectId.value), task_id: taskId, limit: 50 }
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
        limit: 1
      }
    })
    if (res.success && Array.isArray(res.data) && res.data.length > 0) {
      latestMaskArtifact.value = res.data[0]
      config.value.wordcloud_mask_artifact_id = res.data[0].id
    } else {
      latestMaskArtifact.value = null
      config.value.wordcloud_mask_artifact_id = null
    }
  } catch {
    latestMaskArtifact.value = null
  }
}

const handleDatasetChange = async () => {
  pagination.value.current = 1
  await loadDatasetData(1, pagination.value.pageSize)
  await loadAnalysisResults({ skipDataReload: true })
}

const handleTableChange = (pageInfo: any) => {
  loadDatasetData(pageInfo.current, pageInfo.pageSize)
}

const buildArtifactPreviewUrl = (artifactId: number) => `${apiBaseUrl.value}/artifacts/${artifactId}/preview`

const openArtifactPreview = (artifactId: number) => {
  window.open(buildArtifactPreviewUrl(artifactId), '_blank', 'noopener')
}

const clearMaskArtifact = () => {
  latestMaskArtifact.value = null
  config.value.wordcloud_mask_artifact_id = null
  config.value.wc_contour = false
}

const uploadMaskImage = async (options: any) => {
  const formData = new FormData()
  formData.append('project_id', projectId.value)
  formData.append('name', `词云轮廓图_${dayjs().format('YYYYMMDD_HHmmss')}`)
  formData.append('file', options.file)

  try {
    const res: any = await request.post('/artifacts/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    if (res.success) {
      latestMaskArtifact.value = res.data
      config.value.wordcloud_mask_artifact_id = res.data.id
      message.success('轮廓图上传成功')
      options.onSuccess?.(res)
    } else {
      options.onError?.(new Error('上传失败'))
    }
  } catch (error) {
    message.error('轮廓图上传失败')
    options.onError?.(error)
  }
}

const startAnalysis = async () => {
  if (!selectedDatasetId.value) {
    message.warning('请先选择数据集')
    return
  }
  if (!config.value.text_column) {
    message.warning('请选择文本列')
    return
  }
  if (config.value.method === 'deepseek' && !config.value.api_key.trim()) {
    message.warning('使用自定义 LLM API 时请填写 API Key')
    return
  }
  if (config.value.run_lda && config.value.lda_max_k <= config.value.lda_min_k) {
    message.warning('LDA 最大主题数必须大于最小主题数')
    return
  }
  if (config.value.generate_wordcloud && config.value.wordcloud_scopes.length === 0) {
    message.warning('请至少选择一个词云范围')
    return
  }

  submitting.value = true
  try {
    const stopwords = customStopwords.value
      .split(/[\r\n,]+/)
      .map((item) => item.trim())
      .filter(Boolean)

    const payload = {
      ...config.value,
      stopwords
    }
    const res: any = await request.post(`/sentiment/${selectedDatasetId.value}/analyze`, payload)
    if (res.success) {
      lastSubmittedTaskId.value = res.data
      await fetchTaskList()
      message.success('情感分析任务已提交，请在任务中心查看进度')
    }
  } catch (error: any) {
    message.error(error.response?.data?.detail || '提交情感分析任务失败')
  } finally {
    submitting.value = false
  }
}

const loadAnalysisResults = async (options?: { skipDataReload?: boolean; forceDataReload?: boolean }) => {
  if (!selectedDatasetId.value) return
  if (options?.forceDataReload || !options?.skipDataReload) {
    await loadDatasetData(pagination.value.current, pagination.value.pageSize)
  }
  await fetchTaskList()
  const targetTaskId = lastSubmittedTaskId.value || latestSentimentTask.value?.id
  await fetchArtifactsForTask(targetTaskId)
}

const buildSecondPassMessage = (summary: any) => {
  const parts = [
    `高置信度正向样本 ${summary.pseudo_positive_count || 0} 条`,
    `高置信度负向样本 ${summary.pseudo_negative_count || 0} 条`
  ]
  if (summary.trained) {
    return `已完成二次 SnowNLP 训练，${parts.join('，')}`
  }
  if (summary.warning) {
    return `${summary.warning}；${parts.join('，')}`
  }
  return parts.join('，')
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

const formatMetric = (value: any) => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const num = Number(value)
  return Number.isFinite(num) ? num.toFixed(4) : '-'
}

const formatDateTime = (value: string) => {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '-'
}

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

.palette-preview {
  margin-top: 10px;
}

.palette-label {
  margin-bottom: 8px;
  color: var(--text-secondary);
  font-size: 12px;
}

.palette-swatches {
  display: flex;
  gap: 8px;
}

.palette-chip {
  width: 26px;
  height: 14px;
  border-radius: 999px;
  border: 1px solid rgba(0, 0, 0, 0.08);
}

.mask-preview {
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border-radius: 12px;
  background: rgba(244, 247, 253, 0.9);
}

.mask-preview img {
  width: 72px;
  height: 72px;
  object-fit: cover;
  border-radius: 10px;
  border: 1px solid var(--line-soft);
}

.mask-meta {
  flex: 1;
  min-width: 0;
}

.chart-shell {
  min-height: 420px;
}

.wordcloud-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.wordcloud-image {
  width: 100%;
  border-radius: 10px;
  background: #fff;
}

.result-meta {
  color: var(--text-secondary);
  font-size: 12px;
}

.mt-16 {
  margin-top: 16px;
}

.mb-12 {
  margin-bottom: 12px;
}

.mb-16 {
  margin-bottom: 16px;
}
</style>
