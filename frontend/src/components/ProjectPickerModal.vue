<template>
  <a-modal
    :open="visible"
    :title="dialogTitle"
    width="960px"
    :footer="null"
    @cancel="closeModal"
  >
    <div class="picker-toolbar">
      <a-radio-group v-model:value="viewMode" button-style="solid">
        <a-radio-button value="card">窗格视角</a-radio-button>
        <a-radio-button value="table">列表视角</a-radio-button>
      </a-radio-group>
      <a-space>
        <a-button @click="fetchProjects" :loading="loading">刷新</a-button>
        <a-button type="primary" @click="showCreateModal">新建项目</a-button>
      </a-space>
    </div>

    <a-alert
      type="info"
      show-icon
      class="picker-alert"
      message="选择项目后将直接进入目标功能页；如果还没有项目，可以先在这里新建。"
    />

    <a-skeleton active :loading="loading" :paragraph="{ rows: 8 }">
      <div v-if="viewMode === 'card'" class="project-grid">
        <a-card
          v-for="project in projects"
          :key="project.id"
          hoverable
          class="project-card"
          :class="{ active: String(project.id) === activeProjectId }"
          @click="enterProject(project)"
        >
          <div class="project-card-header">
            <div>
              <div class="project-name">{{ project.name }}</div>
              <div class="project-meta">{{ formatDate(project.created_at) }}</div>
            </div>
            <a-tag :color="project.is_archived ? 'red' : 'green'">
              {{ project.is_archived ? '已归档' : '活跃' }}
            </a-tag>
          </div>
          <p class="project-desc">{{ project.description || '暂无描述' }}</p>
          <div class="project-footer">
            <span>数据集 {{ project.dataset_count || 0 }}</span>
            <a-button type="link">进入</a-button>
          </div>
        </a-card>
        <a-empty v-if="!projects.length" description="暂无项目，先新建一个吧" />
      </div>

      <a-table
        v-else
        :columns="columns"
        :data-source="projects"
        row-key="id"
        :pagination="{ pageSize: 8 }"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <a @click="enterProject(record)">{{ record.name }}</a>
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'status'">
            <a-tag :color="record.is_archived ? 'red' : 'green'">
              {{ record.is_archived ? '已归档' : '活跃' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'action'">
            <a-button type="link" @click="enterProject(record)">进入</a-button>
          </template>
        </template>
      </a-table>
    </a-skeleton>

    <a-modal
      v-model:open="createVisible"
      title="创建项目"
      :confirm-loading="submitLoading"
      @ok="submitProject"
    >
      <a-form ref="formRef" :model="createForm" layout="vertical">
        <a-form-item label="项目名称" name="name" :rules="[{ required: true, message: '请输入项目名称' }]">
          <a-input v-model:value="createForm.name" placeholder="输入项目名称" />
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="createForm.description" :rows="4" placeholder="输入项目描述" />
        </a-form-item>
      </a-form>
    </a-modal>
  </a-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'

import request from '@/utils/request'
import { useProjectStore } from '@/store/modules/project'

const props = withDefaults(
  defineProps<{
    open: boolean
    targetRouteName: string
    dialogTitle?: string
    defaultView?: 'card' | 'table'
  }>(),
  {
    dialogTitle: '选择项目',
    defaultView: 'card'
  }
)

const emit = defineEmits<{
  (e: 'update:open', value: boolean): void
}>()

const router = useRouter()
const projectStore = useProjectStore()

const visible = computed(() => props.open)
const dialogTitle = computed(() => props.dialogTitle || '选择项目')
const activeProjectId = computed(() => String(projectStore.currentProjectId || ''))

const loading = ref(false)
const projects = ref<any[]>([])
const viewMode = ref<'card' | 'table'>(props.defaultView)
const createVisible = ref(false)
const submitLoading = ref(false)
const formRef = ref()
const createForm = ref({
  name: '',
  description: ''
})

const columns = [
  { title: '项目名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '数据集数量', dataIndex: 'dataset_count', key: 'dataset_count', width: 120 },
  { title: '状态', key: 'status', width: 100 },
  { title: '创建时间', key: 'created_at', width: 180 },
  { title: '操作', key: 'action', width: 80 }
]

const fetchProjects = async () => {
  loading.value = true
  try {
    const res: any = await request.get('/projects/', { params: { include_archived: true } })
    if (res.success) {
      projects.value = res.data || []
    }
  } catch {
    message.error('获取项目列表失败')
  } finally {
    loading.value = false
  }
}

watch(
  () => props.open,
  (open) => {
    if (open) {
      viewMode.value = props.defaultView
      fetchProjects()
    }
  }
)

const closeModal = () => {
  emit('update:open', false)
}

const showCreateModal = () => {
  createForm.value = { name: '', description: '' }
  createVisible.value = true
}

const submitProject = async () => {
  try {
    await formRef.value?.validate()
    submitLoading.value = true
    const res: any = await request.post('/projects/', {
      name: createForm.value.name,
      description: createForm.value.description,
      is_archived: false
    })
    if (res.success) {
      message.success('项目创建成功')
      createVisible.value = false
      await fetchProjects()
    }
  } catch {
    // 表单校验或请求失败时，错误提示已由上层处理
  } finally {
    submitLoading.value = false
  }
}

const enterProject = (project: any) => {
  projectStore.setCurrentProject(String(project.id))
  closeModal()
  router.push({ name: props.targetRouteName, params: { projectId: String(project.id) } })
}

const formatDate = (dateStr: string) => {
  return dateStr ? dayjs(dateStr).format('YYYY-MM-DD HH:mm') : '-'
}
</script>

<style scoped>
.picker-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.picker-alert {
  margin-bottom: 16px;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.project-card {
  border-radius: 16px;
  border: 1px solid var(--line-soft);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(245, 248, 255, 0.92));
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.project-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 28px rgba(48, 88, 156, 0.12);
}

.project-card.active {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px rgba(99, 132, 201, 0.18);
}

.project-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 12px;
}

.project-name {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary);
}

.project-meta {
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 12px;
}

.project-desc {
  min-height: 48px;
  margin: 0 0 16px;
  color: var(--text-secondary);
}

.project-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  color: var(--text-secondary);
}
</style>
