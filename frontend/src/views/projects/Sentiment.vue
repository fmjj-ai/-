<template>
  <div class="sentiment-container">
    <a-row :gutter="24" style="height: 100%;">
      <a-col :span="8" class="left-panel">
        <a-card title="情感分析与 NLP" :bordered="false" class="neumorphism-card h-full" style="overflow-y: auto;">
          <a-form layout="vertical">
            <a-form-item label="选择数据集">
              <a-select v-model:value="selectedDatasetId" @change="handleDatasetChange" placeholder="请选择数据集" style="width: 100%">
                <a-select-option v-for="d in datasets" :key="d.id" :value="d.id">
                  {{ d.name }}
                </a-select-option>
              </a-select>
            </a-form-item>

            <a-divider />

            <template v-if="selectedDatasetId">
              <a-form-item label="文本列选择">
                <a-select v-model:value="config.text_column" placeholder="选择包含评论文本的列">
                  <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                </a-select>
              </a-form-item>

              <a-form-item label="分析模型">
                <a-select v-model:value="config.method" @change="handleMethodChange">
                  <a-select-option value="snownlp">SnowNLP (内置本地)</a-select-option>
                  <a-select-option value="deepseek">自定义 LLM API</a-select-option>
                </a-select>
                <a-alert v-if="config.method === 'deepseek'" type="warning" show-icon style="margin-top: 8px;">
                  <template #message>
                    提示：这里按 OpenAI 兼容接口填写。未填写 API Key 或模型名称时后端会直接拒绝提交。
                  </template>
                </a-alert>
              </a-form-item>

              <template v-if="config.method === 'deepseek'">
                <a-form-item label="API Key">
                  <a-input-password v-model:value="config.api_key" placeholder="sk-..." allow-clear />
                </a-form-item>
                <a-form-item label="Base URL">
                  <a-input v-model:value="config.base_url" placeholder="例如：https://api.deepseek.com/v1" allow-clear />
                </a-form-item>
                <a-form-item label="模型名称">
                  <a-input v-model:value="config.model_name" placeholder="例如：deepseek-chat / gpt-4o-mini / qwen-plus" allow-clear />
                </a-form-item>
              </template>

              <a-form-item label="自定义停用词 (逗号分隔或换行)">
                <a-textarea v-model:value="customStopwords" placeholder="例如：的,了,呢,啊" :rows="2" />
                <div style="margin-top: 8px;">
                  <a-upload accept=".txt" :before-upload="handleStopwordsUpload" :show-upload-list="false">
                    <a-button size="small">上传停用词表 (.txt)</a-button>
                  </a-upload>
                </div>
              </a-form-item>

              <a-alert
                type="info"
                show-icon
                style="margin-bottom: 16px;"
                message="说明：前端仅保留后端真实生效的配置；高置信度语料导出与前端上传 Mask 暂未接入后端，已移除以避免假配置。"
              />

              <a-divider />

              <a-form-item>
                <a-checkbox v-model:checked="config.extract_tfidf">提取 TF-IDF 关键词</a-checkbox>
              </a-form-item>

              <a-form-item v-if="config.extract_tfidf" label="提取数量 (Top K)">
                <a-input-number v-model:value="config.top_k" :min="5" :max="100" />
              </a-form-item>

              <a-divider />

              <a-form-item>
                <a-checkbox v-model:checked="config.run_lda">执行 LDA 主题提取</a-checkbox>
              </a-form-item>
              <template v-if="config.run_lda">
                <a-form-item label="候选主题数范围（用于困惑度评估）">
                  <a-row :gutter="8">
                    <a-col :span="10">
                      <a-input-number v-model:value="config.lda_min_k" :min="2" placeholder="最小主题数" style="width: 100%" />
                    </a-col>
                    <a-col :span="4" style="text-align: center;">-</a-col>
                    <a-col :span="10">
                      <a-input-number v-model:value="config.lda_max_k" :min="config.lda_min_k + 1" placeholder="最大主题数" style="width: 100%" />
                    </a-col>
                  </a-row>
                </a-form-item>
                <a-form-item label="最终选择主题数 (K)">
                  <a-input-number v-model:value="config.lda_k" :min="2" :max="50" style="width: 100%" />
                </a-form-item>
                <a-form-item>
                  <a-checkbox v-model:checked="config.generate_lda_vis">生成 LDA 交互可视化（较慢）</a-checkbox>
                </a-form-item>
              </template>

              <a-divider />

              <a-form-item>
                <a-checkbox v-model:checked="config.generate_wordcloud" :disabled="!config.extract_tfidf">生成高级词云图</a-checkbox>
              </a-form-item>

              <template v-if="config.generate_wordcloud">
                <a-form-item label="词云主题色卡">
                  <a-select v-model:value="config.wc_colormap">
                    <a-select-option value="viridis">Viridis</a-select-option>
                    <a-select-option value="plasma">Plasma</a-select-option>
                    <a-select-option value="magma">Magma</a-select-option>
                    <a-select-option value="coolwarm">Coolwarm</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="字体">
                  <a-select v-model:value="config.wc_font">
                    <a-select-option value="SimHei">黑体</a-select-option>
                    <a-select-option value="SimSun">宋体</a-select-option>
                    <a-select-option value="Microsoft YaHei">微软雅黑</a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item>
                  <a-checkbox v-model:checked="config.wc_contour">启用轮廓描边（仅后端存在有效 mask 时生效）</a-checkbox>
                </a-form-item>
              </template>

              <a-divider />

              <a-button type="primary" block @click="startAnalysis" :loading="submitting">
                开始分析
              </a-button>

              <a-divider />
              <a-button type="default" block @click="loadAnalysisResults({ forceDataReload: true })">
                刷新结果图表
              </a-button>
            </template>
          </a-form>
        </a-card>
      </a-col>

      <a-col :span="16" class="right-panel">
        <a-card title="结果展示" :bordered="false" class="neumorphism-card h-full" style="overflow-y: auto;">
          <a-tabs v-model:activeKey="activeTab">
            <a-tab-pane key="data" tab="数据预览">
              <a-skeleton active :loading="tableLoading" :paragraph="{ rows: 10 }">
                <a-table
                  :columns="tableColumns"
                  :data-source="tableData"
                  :pagination="pagination"
                  @change="handleTableChange"
                  size="small"
                  :scroll="{ x: 'max-content' }"
                />
              </a-skeleton>
            </a-tab-pane>
            <a-tab-pane key="chart" tab="情感分布图">
              <div v-if="hasSentimentData" style="height: 400px;">
                <Chart :options="sentimentChartOptions" />
              </div>
              <a-empty v-else description="暂无情感分析结果，请先执行分析或刷新" />
            </a-tab-pane>
            <a-tab-pane key="wordcloud" tab="最新词云产物">
              <div v-if="latestWordcloudUrl" style="text-align: center;">
                <img :src="latestWordcloudUrl" alt="Wordcloud" style="max-width: 100%; max-height: 500px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);" />
              </div>
              <a-empty v-else description="暂无词云产物，请确保在分析时勾选了生成词云图" />
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import request from '@/utils/request'
import Chart from '@/components/Chart.vue'
import { useTaskStore } from '@/store/modules/task'

const route = useRoute()
const taskStore = useTaskStore()
const projectId = computed(() => route.params.projectId)

const datasets = ref<any[]>([])
const selectedDatasetId = ref<number | null>(null)
const columns = ref<string[]>([])
const lastSubmittedTaskId = ref<string | null>(null)

const config = ref({
  text_column: '',
  method: 'snownlp',
  api_key: '',
  base_url: 'https://api.deepseek.com/v1',
  model_name: 'deepseek-chat',
  stopwords: [] as string[],
  extract_tfidf: true,
  top_k: 20,
  run_lda: false,
  lda_min_k: 2,
  lda_max_k: 10,
  lda_k: 5,
  generate_lda_vis: false,
  generate_wordcloud: true,
  wc_colormap: 'viridis',
  wc_font: 'SimHei',
  wc_contour: false
})
const customStopwords = ref('')
const submitting = ref(false)
const activeTab = ref('data')

const tableColumns = ref<any[]>([])
const tableData = ref<any[]>([])
const tableLoading = ref(false)
const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true
})

const hasSentimentData = ref(false)
const sentimentChartOptions = ref<any>({})
const latestWordcloudUrl = ref<string | null>(null)

const handleMethodChange = (val: string) => {
  if (val !== 'deepseek') {
    config.value.api_key = ''
    config.value.base_url = 'https://api.deepseek.com/v1'
    config.value.model_name = 'deepseek-chat'
  }
}

const handleStopwordsUpload = (file: File) => {
  const reader = new FileReader()
  reader.onload = (e) => {
    const text = e.target?.result as string
    if (text) {
      const words = text.split(/[\r\n,]+/).map(w => w.trim()).filter(w => w)
      const currentWords = customStopwords.value ? customStopwords.value.split(/[\r\n,]+/).map(w => w.trim()).filter(w => w) : []
      const merged = Array.from(new Set([...currentWords, ...words]))
      customStopwords.value = merged.join(',')
      message.success(`成功导入 ${words.length} 个停用词`)
    }
  }
  reader.readAsText(file)
  return false
}

const fetchDatasets = async () => {
  try {
    const res: any = await request.get(`/datasets/project/${projectId.value}`)
    if (res.success) {
      datasets.value = res.data
    }
  } catch {
    message.error('获取数据集失败')
  }
}

const resetAnalysisView = () => {
  hasSentimentData.value = false
  sentimentChartOptions.value = {}
  latestWordcloudUrl.value = null
}

const handleDatasetChange = async () => {
  if (!selectedDatasetId.value) return
  config.value.text_column = ''
  resetAnalysisView()
  await loadDatasetData(1, pagination.value.pageSize)
  await loadAnalysisResults({ skipDataReload: true })
}

const loadDatasetData = async (page: number, pageSize: number) => {
  if (!selectedDatasetId.value) return
  tableLoading.value = true
  try {
    const res: any = await request.get(`/datasets/${selectedDatasetId.value}/data`, {
      params: { page, size: pageSize }
    })
    if (res.success) {
      const data = res.data
      tableData.value = data.items || []
      pagination.value.total = data.total || 0
      pagination.value.current = page
      pagination.value.pageSize = pageSize
      if (data.columns) {
        columns.value = data.columns
        tableColumns.value = data.columns.map((col: string) => ({
          title: col,
          dataIndex: col,
          key: col,
          ellipsis: true,
          width: 150
        }))
        if (!config.value.text_column && columns.value.length > 0) {
          config.value.text_column = columns.value[0]
        }
      }
    }
  } catch {
    message.error('加载数据失败')
  } finally {
    tableLoading.value = false
  }
}

const handleTableChange = (pag: any) => {
  loadDatasetData(pag.current, pag.pageSize)
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
  if (config.value.method === 'deepseek' && !config.value.model_name.trim()) {
    message.warning('使用自定义 LLM API 时请填写模型名称')
    return
  }
  if (config.value.run_lda && config.value.lda_max_k <= config.value.lda_min_k) {
    message.warning('LDA 最大主题数必须大于最小主题数')
    return
  }

  const stopwordsArray = customStopwords.value
    .split(/[\r\n,]+/)
    .map(s => s.trim())
    .filter(s => s)

  const payload = {
    ...config.value,
    stopwords: stopwordsArray,
    generate_wordcloud: config.value.extract_tfidf ? config.value.generate_wordcloud : false
  }

  submitting.value = true
  try {
    const res: any = await request.post(`/sentiment/${selectedDatasetId.value}/analyze`, payload)
    if (res.success) {
      lastSubmittedTaskId.value = res.data
      message.success('情感分析任务已提交，请在全局任务中心查看进度')
    } else {
      message.error(res.error?.message || '提交任务失败')
    }
  } catch {
    message.error('提交任务失败')
  } finally {
    submitting.value = false
  }
}

const fetchLatestWordcloud = async () => {
  const baseParams: Record<string, string | number> = {
    project_id: Number(projectId.value),
    type: 'png',
    name_prefix: '词云图_',
    limit: 1,
  }

  const candidateTaskIds = [lastSubmittedTaskId.value]
    .filter((taskId): taskId is string => Boolean(taskId))

  for (const taskId of candidateTaskIds) {
    try {
      const res: any = await request.get('/artifacts/', {
        params: {
          ...baseParams,
          task_id: taskId,
        }
      })
      if (res.success && Array.isArray(res.data) && res.data.length > 0) {
        return `/api/artifacts/${res.data[0].id}/download`
      }
    } catch (error) {
      console.error('Failed to load wordcloud by task filter', error)
    }
  }

  const fallbackRes: any = await request.get('/artifacts/', {
    params: baseParams
  })
  if (fallbackRes.success && Array.isArray(fallbackRes.data) && fallbackRes.data.length > 0) {
    return `/api/artifacts/${fallbackRes.data[0].id}/download`
  }
  return null
}

const loadAnalysisResults = async (options?: { skipDataReload?: boolean; forceDataReload?: boolean }) => {
  if (!selectedDatasetId.value) return

  const shouldReloadData = options?.forceDataReload || !options?.skipDataReload
  if (shouldReloadData) {
    await loadDatasetData(pagination.value.current, pagination.value.pageSize)
  }

  const hasSentimentColumn = columns.value.includes('sentiment_label')
  hasSentimentData.value = hasSentimentColumn
  if (!hasSentimentColumn) {
    sentimentChartOptions.value = {}
    latestWordcloudUrl.value = null
    return
  }

  try {
    const statRes: any = await request.post(`/statistics/${selectedDatasetId.value}/descriptive`, {
      columns: ['sentiment_label']
    })

    if (statRes.success) {
      const catStats = statRes.data.categorical || {}
      const labelStats = catStats['sentiment_label']?.top_values || {}
      sentimentChartOptions.value = {
        title: { text: '情感分布', left: 'center' },
        tooltip: { trigger: 'item' },
        legend: { orient: 'vertical', left: 'left' },
        series: [
          {
            name: '情感',
            type: 'pie',
            radius: '50%',
            data: Object.keys(labelStats).map(k => ({ name: k, value: labelStats[k] })),
            emphasis: {
              itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' }
            }
          }
        ]
      }
    }

    latestWordcloudUrl.value = await fetchLatestWordcloud()
  } catch (e) {
    console.error('Failed to load analysis results', e)
  }
}

const handleTaskUpdate = async (event: MessageEvent) => {
  if (event.data === 'ping' || !selectedDatasetId.value) return

  try {
    const payload = JSON.parse(event.data)
    if (payload.status !== 'completed') return

    const result = payload.result || {}
    const isSentimentTask = result.kind === 'sentiment_analysis' || result.dataset_id === selectedDatasetId.value
    if (!isSentimentTask) return

    if (lastSubmittedTaskId.value && payload.task_id !== lastSubmittedTaskId.value && result.dataset_id !== selectedDatasetId.value) {
      return
    }

    await loadAnalysisResults({ forceDataReload: true })
    await fetchDatasets()
    message.success('情感分析结果已自动刷新')
  } catch (error) {
    console.error('Task stream parse failed', error)
  }
}

onMounted(() => {
  fetchDatasets()
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
  height: calc(100vh - 120px);
  background-color: var(--bg-color);
}
.left-panel, .right-panel {
  height: 100%;
}
</style>
