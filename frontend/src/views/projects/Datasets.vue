<template>
  <div class="datasets-container">
    <a-row :gutter="24" style="height: 100%;">
      <a-col :span="6" class="left-panel">
        <a-card title="数据集列表" :bordered="false" class="neumorphism-card h-full">
          <template #extra>
            <a-upload
              name="file"
              :showUploadList="false"
              :customRequest="customUpload"
            >
              <a-button type="primary" :loading="uploading">导入数据</a-button>
            </a-upload>
          </template>
          <a-list :dataSource="datasets" :loading="datasetsLoading">
            <template #renderItem="{ item }">
              <a-list-item 
                @click="selectDataset(item)" 
                :class="{'selected-item': currentDataset?.id === item.id}"
                style="cursor: pointer; padding: 12px;"
              >
                <a-list-item-meta :description="item.status === 'ready' ? `行数: ${item.row_count}` : item.status">
                  <template #title>
                    {{ item.name }}
                  </template>
                </a-list-item-meta>
                <template #actions>
                  <a-popconfirm title="确定要删除？" @confirm.stop="deleteDataset(item.id)">
                    <a-button type="text" danger size="small" @click.stop>删除</a-button>
                  </a-popconfirm>
                </template>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>

      <a-col :span="18" class="right-panel">
        <a-card v-if="currentDataset" :title="currentDataset.name" :bordered="false" class="neumorphism-card h-full">
          <template #extra>
            <a-space>
              <a-button @click="showSnapshots">版本快照</a-button>
              <a-button type="primary" @click="createSnapshot" :loading="snapshotLoading">生成快照</a-button>
            </a-space>
          </template>
          
          <div v-if="currentDataset.status === 'ready'">
            <a-alert style="margin-bottom: 16px;" message="双击单元格即可进行编辑" type="info" show-icon />
            <a-skeleton active :loading="tableLoading" :paragraph="{ rows: 10 }">
              <a-table
                :columns="tableColumns"
                :data-source="tableData"
                :pagination="pagination"
                @change="handleTableChange"
                bordered
                size="middle"
                :scroll="{ x: 'max-content', y: 500 }"
              >
                <template #bodyCell="{ column, record }">
                  <div 
                    class="editable-cell" 
                    @dblclick="editCell(record, column.dataIndex)"
                  >
                    <a-input
                      v-if="editingCell?.rowKey === record._row_index && editingCell?.colKey === column.dataIndex"
                      v-model:value="editingValue"
                      size="small"
                      @blur="saveCell(record, column.dataIndex)"
                      @pressEnter="saveCell(record, column.dataIndex)"
                      auto-focus
                    />
                    <span v-else>{{ record[column.dataIndex] }}</span>
                  </div>
                </template>
              </a-table>
            </a-skeleton>
          </div>
          <div v-else-if="currentDataset.status === 'failed'">
            <a-alert type="error" :message="`导入失败: ${currentDataset.error_message}`" />
          </div>
          <div v-else style="text-align: center; padding: 50px;">
            <a-spin tip="数据处理中..." />
          </div>
        </a-card>
        <div v-else class="empty-state">
          <a-empty description="请选择或导入数据集" />
        </div>
      </a-col>
    </a-row>

    <!-- Snapshots Modal -->
    <a-modal v-model:visible="snapshotsVisible" title="数据集快照" :footer="null">
      <a-table :columns="snapshotColumns" :dataSource="snapshots" :loading="snapshotsLoading" rowKey="id">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
        </template>
      </a-table>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import request from '@/utils/request'
import dayjs from 'dayjs'

const route = useRoute()
const projectId = computed(() => route.params.projectId)

const datasets = ref<any[]>([])
const datasetsLoading = ref(false)
const uploading = ref(false)
const currentDataset = ref<any>(null)

// Table Data
const tableColumns = ref<any[]>([])
const tableData = ref<any[]>([])
const tableLoading = ref(false)
const pagination = ref({
  current: 1,
  pageSize: 50,
  total: 0,
  showSizeChanger: true
})

const fetchDatasets = async () => {
  datasetsLoading.value = true
  try {
    const res: any = await request.get(`/api/datasets/project/${projectId.value}`)
    if (res.success) {
      datasets.value = res.data
      if (currentDataset.value) {
        const updated = datasets.value.find((d: any) => d.id === currentDataset.value.id)
        if (updated) {
          currentDataset.value = updated
          if (updated.status === 'ready' && tableData.value.length === 0) {
            setupTableColumns()
            fetchTableData()
          }
        }
      }
    }
  } catch (e) {
    message.error('获取数据集失败')
  } finally {
    datasetsLoading.value = false
  }
}

const customUpload = async (options: any) => {
  const { file, onSuccess, onError } = options
  const formData = new FormData()
  formData.append('file', file)
  formData.append('project_id', projectId.value as string)

  uploading.value = true
  try {
    const res: any = await request.post('/api/datasets/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
    if (res.success) {
      message.success('上传成功，正在处理中...')
      fetchDatasets()
      onSuccess(res, file)
    } else {
      onError(new Error('上传失败'))
    }
  } catch (e) {
    message.error('上传失败')
    onError(e)
  } finally {
    uploading.value = false
  }
}

const deleteDataset = async (id: number) => {
  try {
    const res: any = await request.delete(`/api/datasets/${id}`)
    if (res.success) {
      message.success('删除成功')
      if (currentDataset.value?.id === id) {
        currentDataset.value = null
        tableData.value = []
      }
      fetchDatasets()
    }
  } catch (e) {
    message.error('删除失败')
  }
}

const setupTableColumns = () => {
  if (currentDataset.value && currentDataset.value.schema_info) {
    tableColumns.value = currentDataset.value.schema_info.map((col: any) => ({
      title: col.name,
      dataIndex: col.name,
      key: col.name,
      width: 150
    }))
  }
}

const selectDataset = (dataset: any) => {
  currentDataset.value = dataset
  pagination.value.current = 1
  if (dataset.status === 'ready') {
    setupTableColumns()
    fetchTableData()
  } else {
    tableData.value = []
  }
}

const fetchTableData = async () => {
  if (!currentDataset.value || currentDataset.value.status !== 'ready') return
  
  tableLoading.value = true
  try {
    const res: any = await request.get(`/api/datasets/${currentDataset.value.id}/data`, {
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

// Editing
const editingCell = ref<{rowKey: number, colKey: string} | null>(null)
const editingValue = ref('')

const editCell = (record: any, colKey: string) => {
  editingCell.value = { rowKey: record._row_index, colKey }
  editingValue.value = record[colKey]
}

const saveCell = async (record: any, colKey: string) => {
  if (!editingCell.value) return
  const originalValue = record[colKey]
  if (editingValue.value !== originalValue) {
    // Update backend
    try {
      const res: any = await request.put(`/api/datasets/${currentDataset.value.id}/data`, {
        row_index: record._row_index,
        updates: { [colKey]: editingValue.value }
      })
      if (res.success) {
        record[colKey] = editingValue.value
        message.success('修改成功')
      }
    } catch (e) {
      message.error('修改失败')
    }
  }
  editingCell.value = null
}

// Snapshots
const snapshotLoading = ref(false)
const snapshotsVisible = ref(false)
const snapshots = ref<any[]>([])
const snapshotsLoading = ref(false)

const snapshotColumns = [
  { title: '版本', dataIndex: 'version', key: 'version' },
  { title: '行数', dataIndex: 'row_count', key: 'row_count' },
  { title: '列数', dataIndex: 'col_count', key: 'col_count' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' }
]

const createSnapshot = async () => {
  snapshotLoading.value = true
  try {
    const res: any = await request.post(`/api/datasets/${currentDataset.value.id}/snapshot`)
    if (res.success) {
      message.success('快照创建成功')
    }
  } catch (e) {
    message.error('快照创建失败')
  } finally {
    snapshotLoading.value = false
  }
}

const showSnapshots = async () => {
  snapshotsVisible.value = true
  snapshotsLoading.value = true
  try {
    const res: any = await request.get(`/api/datasets/${currentDataset.value.id}/snapshots`)
    if (res.success) {
      snapshots.value = res.data
    }
  } catch (e) {
    message.error('获取快照列表失败')
  } finally {
    snapshotsLoading.value = false
  }
}

const formatDate = (dateStr: string) => {
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

// Poll dataset status if not ready
let timer: any = null
onMounted(() => {
  fetchDatasets()
  timer = setInterval(() => {
    if (datasets.value.some(d => d.status === 'importing')) {
      fetchDatasets()
    }
  }, 3000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

</script>

<style scoped>
.datasets-container {
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
.selected-item {
  background-color: var(--primary-soft);
  border-radius: 8px;
}
.empty-state {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.editable-cell {
  min-height: 24px;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  transition: background-color 0.3s;
}
.editable-cell:hover {
  background-color: var(--bg-base);
}
</style>
