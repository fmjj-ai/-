<template>
  <div class="processing-container">
    <a-row :gutter="24" style="height: 100%;">
      <a-col :span="6" class="left-panel">
        <a-card title="数据处理与变换" :bordered="false" class="neumorphism-card h-full" style="overflow-y: auto;">
          <a-form layout="vertical">
            <a-form-item label="选择数据集">
              <a-select v-model:value="selectedDatasetId" @change="handleDatasetChange" placeholder="请选择数据集" style="width: 100%">
                <a-select-option v-for="d in datasets" :key="d.id" :value="d.id">
                  {{ d.name }}
                </a-select-option>
              </a-select>
            </a-form-item>

            <a-divider />

            <a-collapse v-model:activeKey="activeKey" v-if="selectedDatasetId">
              <a-collapse-panel key="1" header="数据清洗 (ST-01)">
                <a-form-item label="操作类型">
                  <a-select v-model:value="cleanOp.type" placeholder="请选择清洗操作">
                    <a-select-option value="dropna">删除缺失值</a-select-option>
                    <a-select-option value="fillna">填充缺失值</a-select-option>
                    <a-select-option value="drop_duplicates">去重</a-select-option>
                    <a-select-option value="type_convert">类型转换</a-select-option>
                  </a-select>
                </a-form-item>

                <template v-if="cleanOp.type === 'dropna'">
                  <a-form-item label="目标列 (留空则应用所有列)">
                    <a-select v-model:value="cleanOp.columns" mode="multiple" placeholder="选择列">
                      <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                    </a-select>
                  </a-form-item>
                </template>

                <template v-if="cleanOp.type === 'fillna'">
                  <a-form-item label="目标列">
                    <a-select v-model:value="cleanOp.columns" mode="multiple" placeholder="选择列">
                      <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item label="填充方法">
                    <a-select v-model:value="cleanOp.method">
                      <a-select-option value="mean">均值 (仅数值)</a-select-option>
                      <a-select-option value="median">中位数 (仅数值)</a-select-option>
                      <a-select-option value="mode">众数</a-select-option>
                      <a-select-option value="custom">自定义值</a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item v-if="cleanOp.method === 'custom'" label="自定义值">
                    <a-input v-model:value="cleanOp.value" />
                  </a-form-item>
                </template>

                <template v-if="cleanOp.type === 'type_convert'">
                  <a-form-item label="目标列">
                    <a-select v-model:value="cleanOp.column">
                      <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item label="目标类型">
                    <a-select v-model:value="cleanOp.target_type">
                      <a-select-option value="numeric">数值型</a-select-option>
                      <a-select-option value="string">字符串</a-select-option>
                      <a-select-option value="datetime">日期时间</a-select-option>
                    </a-select>
                  </a-form-item>
                </template>

                <a-button type="primary" block @click="applyCleanOp" :loading="processing">应用清洗</a-button>
              </a-collapse-panel>

              <a-collapse-panel key="2" header="数据变换 (ST-02)">
                <a-form-item label="操作类型">
                  <a-select v-model:value="transformOp.type">
                    <a-select-option value="compute_column">新增计算列</a-select-option>
                    <a-select-option value="normalize">数据标准化</a-select-option>
                  </a-select>
                </a-form-item>

                <template v-if="transformOp.type === 'compute_column'">
                  <a-form-item label="新列名">
                    <a-input v-model:value="transformOp.new_column" />
                  </a-form-item>
                  <a-form-item label="计算表达式 (如: colA + colB)">
                    <a-input v-model:value="transformOp.expression" />
                  </a-form-item>
                </template>

                <template v-if="transformOp.type === 'normalize'">
                  <a-form-item label="目标列">
                    <a-select v-model:value="transformOp.columns" mode="multiple">
                      <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
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

              <a-collapse-panel key="3" header="特征编码 (PR-02/03)">
                <a-form-item label="编码类型">
                  <a-select v-model:value="encodeOp.type">
                    <a-select-option value="one_hot_encode">独热编码 (One-Hot)</a-select-option>
                    <a-select-option value="multi_hot_encode">多热编码 (Multi-Hot)</a-select-option>
                  </a-select>
                </a-form-item>

                <template v-if="encodeOp.type === 'one_hot_encode'">
                  <a-form-item label="目标列">
                    <a-select v-model:value="encodeOp.columns" mode="multiple">
                      <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                    </a-select>
                  </a-form-item>
                </template>

                <template v-if="encodeOp.type === 'multi_hot_encode'">
                  <a-form-item label="目标列">
                    <a-select v-model:value="encodeOp.column">
                      <a-select-option v-for="col in columns" :key="col" :value="col">{{ col }}</a-select-option>
                    </a-select>
                  </a-form-item>
                  <a-form-item label="分隔符">
                    <a-input v-model:value="encodeOp.separator" placeholder="如: ," />
                  </a-form-item>
                </template>

                <a-form-item>
                  <a-checkbox v-model:checked="encodeOp.keep_original">保留原始列</a-checkbox>
                </a-form-item>

                <a-button type="primary" block @click="applyEncodeOp" :loading="processing">应用编码</a-button>
              </a-collapse-panel>
            </a-collapse>
          </a-form>
        </a-card>
      </a-col>

      <a-col :span="18" class="right-panel">
        <a-card title="数据预览" :bordered="false" class="neumorphism-card h-full">
          <div v-if="selectedDatasetId">
            <a-skeleton active :loading="tableLoading" :paragraph="{ rows: 10 }">
              <a-table
                :columns="tableColumns"
                :data-source="tableData"
                :pagination="pagination"
                @change="handleTableChange"
                bordered
                size="middle"
                :scroll="{ x: 'max-content', y: 'calc(100vh - 250px)' }"
              />
            </a-skeleton>
          </div>
          <div v-else class="empty-state">
            <a-empty description="请在左侧选择数据集" />
          </div>
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

const route = useRoute()
const projectId = computed(() => route.params.projectId)

const datasets = ref<any[]>([])
const selectedDatasetId = ref<number | null>(null)
const currentDataset = ref<any>(null)

const activeKey = ref(['1'])
const processing = ref(false)

// Table Data
const columns = ref<string[]>([])
const tableColumns = ref<any[]>([])
const tableData = ref<any[]>([])
const tableLoading = ref(false)
const pagination = ref({
  current: 1,
  pageSize: 50,
  total: 0,
  showSizeChanger: true
})

// Operations state
const cleanOp = ref<any>({ type: 'dropna', columns: [], method: 'mean', value: '', column: '', target_type: 'numeric' })
const transformOp = ref<any>({ type: 'compute_column', new_column: '', expression: '', columns: [], method: 'minmax' })
const encodeOp = ref<any>({ type: 'one_hot_encode', columns: [], column: '', separator: ',', keep_original: false })

const fetchDatasets = async () => {
  try {
    const res: any = await request.get(`/api/datasets/project/${projectId.value}`)
    if (res.success) {
      datasets.value = res.data.filter((d: any) => d.status === 'ready')
    }
  } catch (e) {
    message.error('获取数据集失败')
  }
}

const handleDatasetChange = async () => {
  currentDataset.value = datasets.value.find(d => d.id === selectedDatasetId.value)
  if (currentDataset.value) {
    updateColumnsList()
    pagination.value.current = 1
    await fetchTableData()
  }
}

const updateColumnsList = () => {
  if (currentDataset.value && currentDataset.value.schema_info) {
    columns.value = currentDataset.value.schema_info.map((c: any) => c.name)
    tableColumns.value = currentDataset.value.schema_info.map((col: any) => ({
      title: col.name,
      dataIndex: col.name,
      key: col.name,
      width: 150
    }))
  }
}

const fetchTableData = async () => {
  if (!selectedDatasetId.value) return
  
  tableLoading.value = true
  try {
    const res: any = await request.get(`/api/datasets/${selectedDatasetId.value}/data`, {
      params: {
        page: pagination.value.current,
        size: pagination.value.pageSize
      }
    })
    if (res.success) {
      tableData.value = res.data.items
      pagination.value.total = res.data.total
    }
  } catch (e) {
    message.error('获取表格数据失败')
  } finally {
    tableLoading.value = false
  }
}

const handleTableChange = (pag: any) => {
  pagination.value.current = pag.current
  pagination.value.pageSize = pag.pageSize
  fetchTableData()
}

const executeOperation = async (operation: any) => {
  if (!selectedDatasetId.value) return
  
  processing.value = true
  try {
    const res: any = await request.post(`/api/processing/${selectedDatasetId.value}/process`, [operation])
    if (res.success) {
      message.success('操作成功')
      // Refetch dataset schema
      const dsRes: any = await request.get(`/api/datasets/${selectedDatasetId.value}`)
      if (dsRes.success) {
        currentDataset.value = dsRes.data
        updateColumnsList()
        await fetchTableData()
      }
    }
  } catch (e: any) {
    message.error(e.response?.data?.detail || '处理失败')
  } finally {
    processing.value = false
  }
}

const applyCleanOp = () => {
  const op = { type: cleanOp.value.type, params: { ...cleanOp.value } }
  executeOperation(op)
}

const applyTransformOp = () => {
  const op = { type: transformOp.value.type, params: { ...transformOp.value } }
  executeOperation(op)
}

const applyEncodeOp = () => {
  const op = { type: encodeOp.value.type, params: { ...encodeOp.value } }
  executeOperation(op)
}

onMounted(() => {
  fetchDatasets()
})
</script>

<style scoped>
.processing-container {
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
.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
