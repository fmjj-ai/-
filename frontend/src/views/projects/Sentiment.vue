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
                <a-select v-model:value="config.method">
                  <a-select-option value="snownlp">SnowNLP (内置本地)</a-select-option>
                  <a-select-option value="deepseek" disabled>DeepSeek API (即将支持)</a-select-option>
                </a-select>
              </a-form-item>

              <a-form-item label="自定义停用词 (逗号分隔)">
                <a-textarea v-model:value="customStopwords" placeholder="例如：的,了,呢,啊" :rows="2" />
              </a-form-item>

              <a-form-item>
                <a-checkbox v-model:checked="config.extract_tfidf">提取 TF-IDF 关键词</a-checkbox>
              </a-form-item>

              <a-form-item v-if="config.extract_tfidf" label="提取数量 (Top K)">
                <a-input-number v-model:value="config.top_k" :min="5" :max="100" />
              </a-form-item>

              <a-form-item>
                <a-checkbox v-model:checked="config.generate_wordcloud" :disabled="!config.extract_tfidf">生成词云图导出</a-checkbox>
              </a-form-item>

              <a-button type="primary" block @click="startAnalysis" :loading="submitting">
                开始分析
              </a-button>
              
              <a-divider />
              <a-button type="default" block @click="loadAnalysisResults">
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
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import request from '@/utils/request'
import Chart from '@/components/Chart.vue'

const route = useRoute()
const projectId = computed(() => route.params.projectId)

const datasets = ref<any[]>([])
const selectedDatasetId = ref<number | null>(null)
const columns = ref<string[]>([])

const config = ref({
  text_column: '',
  method: 'snownlp',
  stopwords: [],
  extract_tfidf: true,
  top_k: 20,
  generate_wordcloud: true
})
const customStopwords = ref('')
const submitting = ref(false)

const activeTab = ref('data')

// Table State
const tableColumns = ref<any[]>([])
const tableData = ref<any[]>([])
const tableLoading = ref(false)
const pagination = ref({
  current: 1,
  pageSize: 10,
  total: 0,
  showSizeChanger: true
})

// Chart & Artifacts State
const hasSentimentData = ref(false)
const sentimentChartOptions = ref<any>({})
const latestWordcloudUrl = ref<string | null>(null)

const fetchDatasets = async () => {
  try {
    const res = await request.get(`/api/datasets/?project_id=${projectId.value}`)
    if (res.data?.success) {
      datasets.value = res.data.data
    }
  } catch (error) {
    message.error('获取数据集失败')
  }
}

const handleDatasetChange = async () => {
  if (!selectedDatasetId.value) return
  config.value.text_column = ''
  hasSentimentData.value = false
  latestWordcloudUrl.value = null
  await loadDatasetData(1, pagination.value.pageSize)
  await loadAnalysisResults()
}

const loadDatasetData = async (page: number, pageSize: number) => {
  if (!selectedDatasetId.value) return
  tableLoading.value = true
  try {
    const res = await request.get(`/api/datasets/${selectedDatasetId.value}/data`, {
      params: { page, page_size: pageSize }
    })
    if (res.data?.success) {
      const data = res.data.data
      tableData.value = data.data
      pagination.value.total = data.total
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
        // Auto select first string-like column if not set
        if (!config.value.text_column && columns.value.length > 0) {
          config.value.text_column = columns.value[0]
        }
      }
    }
  } catch (error) {
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

  const stopwordsArray = customStopwords.value.split(',').map(s => s.trim()).filter(s => s)
  
  const payload = {
    ...config.value,
    stopwords: stopwordsArray
  }

  submitting.value = true
  try {
    const res = await request.post(`/api/sentiment/${selectedDatasetId.value}/analyze`, payload)
    if (res.data?.success) {
      message.success('情感分析任务已提交，请在全局任务中心查看进度')
    } else {
      message.error(res.data?.error?.message || '提交任务失败')
    }
  } catch (error) {
    message.error('提交任务失败')
  } finally {
    submitting.value = false
  }
}

const loadAnalysisResults = async () => {
  if (!selectedDatasetId.value) return
  
  // Reload table to see if sentiment columns exist
  await loadDatasetData(pagination.value.current, pagination.value.pageSize)
  
  if (columns.value.includes('sentiment_label')) {
    hasSentimentData.value = true
    // Fetch stats for chart (we can use the statistics endpoint or just calculate from a small sample, but ideally we use statistics endpoint)
    try {
      const statRes = await request.post(`/api/statistics/${selectedDatasetId.value}/descriptive`, {
        columns: ['sentiment_label']
      })
      if (statRes.data?.success) {
        const catStats = statRes.data.data.categorical || {}
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
    } catch (e) {
      console.error('Failed to load chart stats', e)
    }
  }

  // Load artifacts for wordcloud
  try {
    const artRes = await request.get(`/api/artifacts/?project_id=${projectId.value}`)
    if (artRes.data?.success) {
      const artifacts = artRes.data.data
      const wordclouds = artifacts.filter((a: any) => a.name.startsWith('词云图_') && a.type === 'png')
      if (wordclouds.length > 0) {
        // Get the latest one
        const latest = wordclouds[0] // Assuming sorted desc
        latestWordcloudUrl.value = `/api/artifacts/${latest.id}/download`
      }
    }
  } catch (e) {
    console.error('Failed to load artifacts', e)
  }
}

onMounted(() => {
  fetchDatasets()
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
