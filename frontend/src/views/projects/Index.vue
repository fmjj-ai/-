<template>
  <div class="projects-container">
    <div class="header">
      <h2>项目管理</h2>
      <a-button type="primary" @click="showCreateModal">创建项目</a-button>
    </div>

    <a-table 
      :columns="columns" 
      :data-source="projects" 
      :loading="loading" 
      row-key="id"
      class="neumorphism-table"
      :pagination="{ pageSize: 10 }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" @click="goToProject(record)">进入</a-button>
            <a-button type="link" @click="editProject(record)">编辑</a-button>
            <a-popconfirm title="确定要删除这个项目吗？该操作不可恢复！" @confirm="deleteProject(record.id)">
              <a-button type="link" danger>删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
        <template v-else-if="column.key === 'is_archived'">
          <a-tag :color="record.is_archived ? 'red' : 'green'">
            {{ record.is_archived ? '已归档' : '活跃' }}
          </a-tag>
        </template>
        <template v-else-if="column.key === 'created_at'">
          {{ formatDate(record.created_at) }}
        </template>
      </template>
    </a-table>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑项目' : '创建项目'"
      @ok="handleModalOk"
      :confirmLoading="submitLoading"
    >
      <a-form :model="form" layout="vertical" ref="formRef">
        <a-form-item label="项目名称" name="name" :rules="[{ required: true, message: '请输入项目名称' }]">
          <a-input v-model:value="form.name" placeholder="输入项目名称" />
        </a-form-item>
        <a-form-item label="描述" name="description">
          <a-textarea v-model:value="form.description" placeholder="输入项目描述" :rows="4" />
        </a-form-item>
        <a-form-item v-if="isEdit" label="状态" name="is_archived">
          <a-switch v-model:checked="form.is_archived" checked-children="已归档" un-checked-children="活跃" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import request from '@/utils/request'
import { useProjectStore } from '@/store/modules/project'
import dayjs from 'dayjs'

const router = useRouter()
const projectStore = useProjectStore()

const loading = ref(false)
const projects = ref([])

const columns = [
  { title: '项目名称', dataIndex: 'name', key: 'name' },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '数据集数量', dataIndex: 'dataset_count', key: 'dataset_count' },
  { title: '状态', dataIndex: 'is_archived', key: 'is_archived' },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at' },
  { title: '操作', key: 'action', width: 200 }
]

const fetchProjects = async () => {
  loading.value = true
  try {
    const res: any = await request.get('/projects/', { params: { include_archived: true } })
    if (res.success) {
      projects.value = res.data
    }
  } catch (error) {
    message.error('获取项目列表失败')
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr: string) => {
  return dayjs(dateStr).format('YYYY-MM-DD HH:mm:ss')
}

onMounted(() => {
  fetchProjects()
})

const modalVisible = ref(false)
const isEdit = ref(false)
const submitLoading = ref(false)
const formRef = ref()

const form = ref({
  id: null,
  name: '',
  description: '',
  is_archived: false
})

const showCreateModal = () => {
  isEdit.value = false
  form.value = { id: null as any, name: '', description: '', is_archived: false }
  modalVisible.value = true
}

const editProject = (record: any) => {
  isEdit.value = true
  form.value = { 
    id: record.id, 
    name: record.name, 
    description: record.description, 
    is_archived: record.is_archived 
  }
  modalVisible.value = true
}

const handleModalOk = async () => {
  try {
    await formRef.value.validate()
    submitLoading.value = true
    if (isEdit.value) {
      const res: any = await request.put(`/projects/${form.value.id}`, {
        name: form.value.name,
        description: form.value.description,
        is_archived: form.value.is_archived
      })
      if (res.success) {
        message.success('编辑成功')
        modalVisible.value = false
        fetchProjects()
      }
    } else {
      const res: any = await request.post('/projects/', {
        name: form.value.name,
        description: form.value.description,
        is_archived: false
      })
      if (res.success) {
        message.success('创建成功')
        modalVisible.value = false
        fetchProjects()
      }
    }
  } catch (e) {
    // validation error or request error
  } finally {
    submitLoading.value = false
  }
}

const deleteProject = async (id: number) => {
  try {
    const res: any = await request.delete(`/projects/${id}`)
    if (res.success) {
      message.success('删除成功')
      fetchProjects()
    }
  } catch (error) {
    message.error('删除失败')
  }
}

const goToProject = (record: any) => {
  projectStore.setCurrentProject(record.id)
  router.push({ name: 'Datasets', params: { projectId: record.id } })
}

</script>

<style scoped>
.projects-container {
  padding: 24px;
}
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
.header h2 {
  margin: 0;
  color: var(--text-primary);
}
.neumorphism-table {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-outer);
  background: var(--bg-elevated);
  padding: 16px;
}
</style>
