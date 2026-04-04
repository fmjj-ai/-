<template>
  <div class="tasks-container">
    <div class="page-header">
      <h2>任务中心</h2>
      <a-button @click="refreshTasks" :loading="loading">刷新</a-button>
    </div>

    <div class="split-layout">
      <!-- 左侧任务列表 -->
      <div class="task-list-panel">
        <a-list
          :loading="loading"
          item-layout="horizontal"
          :data-source="taskStore.tasks"
        >
          <template #renderItem="{ item }">
            <a-list-item 
              class="task-list-item" 
              :class="{ active: selectedTaskId === item.id }"
              @click="selectTask(item.id)"
            >
              <a-list-item-meta>
                <template #title>
                  <span class="task-name">{{ item.name || '未命名任务' }}</span>
                </template>
                <template #description>
                  <div class="task-meta">
                    <span>{{ item.type }}</span>
                    <span>{{ formatDate(item.created_at) }}</span>
                  </div>
                  <a-progress v-if="item.status === 'running' || item.status === 'pending'" :percent="item.progress || 0" size="small" />
                </template>
              </a-list-item-meta>
              <template #actions>
                <a-tag :color="getStatusColor(item.status)">{{ getStatusText(item.status) }}</a-tag>
              </template>
            </a-list-item>
          </template>
          <template #empty>
            <a-empty description="当前项目暂无任务" />
          </template>
        </a-list>
      </div>

      <!-- 右侧任务详情 -->
      <div class="task-detail-panel">
        <div v-if="selectedTask" class="detail-content">
          <div class="detail-header">
            <h3>{{ selectedTask.name || '未命名任务' }}</h3>
            <div class="detail-actions">
              <a-popconfirm
                title="确定要删除此任务吗？删除后无法恢复"
                ok-text="确定"
                cancel-text="取消"
                @confirm="handleDelete(selectedTask.id)"
              >
                <a-button danger>删除任务</a-button>
              </a-popconfirm>
            </div>
          </div>

          <a-descriptions bordered :column="1" size="small" class="detail-desc">
            <a-descriptions-item label="任务 ID">{{ selectedTask.id }}</a-descriptions-item>
            <a-descriptions-item label="任务类型">{{ selectedTask.type }}</a-descriptions-item>
            <a-descriptions-item label="状态">
              <a-tag :color="getStatusColor(selectedTask.status)">{{ getStatusText(selectedTask.status) }}</a-tag>
            </a-descriptions-item>
            <a-descriptions-item label="进度" v-if="selectedTask.status === 'running' || selectedTask.status === 'pending'">
              <a-progress :percent="selectedTask.progress || 0" />
            </a-descriptions-item>
            <a-descriptions-item label="创建时间">{{ formatDate(selectedTask.created_at) }}</a-descriptions-item>
            <a-descriptions-item label="结束时间" v-if="selectedTask.finished_at">{{ formatDate(selectedTask.finished_at) }}</a-descriptions-item>
          </a-descriptions>

          <div class="detail-section" v-if="selectedTask.error_msg">
            <h4>错误信息</h4>
            <a-alert :message="selectedTask.error_msg" type="error" show-icon />
          </div>

          <div class="detail-section" v-if="selectedTask.result">
            <h4>执行结果</h4>
            <pre class="result-pre">{{ JSON.stringify(selectedTask.result, null, 2) }}</pre>
          </div>
        </div>
        <div v-else class="empty-detail">
          <a-empty description="请在左侧选择一个任务查看详情" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useTaskStore } from '@/store/modules/task';
import { message } from 'ant-design-vue';

const route = useRoute();
const taskStore = useTaskStore();
const projectId = route.params.projectId as string;

const loading = ref(false);
const selectedTaskId = ref<string | null>(null);

const selectedTask = computed(() => {
  if (!selectedTaskId.value) return null;
  return taskStore.tasks.find(t => t.id === selectedTaskId.value) || null;
});

const refreshTasks = async () => {
  loading.value = true;
  await taskStore.fetchTasks(projectId);
  loading.value = false;
};

onMounted(() => {
  refreshTasks();
});

const selectTask = (id: string) => {
  selectedTaskId.value = id;
};

const handleDelete = async (id: string) => {
  try {
    await taskStore.deleteTask(id);
    message.success('任务删除成功');
    if (selectedTaskId.value === id) {
      selectedTaskId.value = null;
    }
  } catch (e) {
    message.error('删除任务失败');
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case 'pending': return 'default';
    case 'running': return 'processing';
    case 'completed': return 'success';
    case 'failed': return 'error';
    default: return 'default';
  }
};

const getStatusText = (status: string) => {
  switch (status) {
    case 'pending': return '等待中';
    case 'running': return '运行中';
    case 'completed': return '已完成';
    case 'failed': return '失败';
    default: return '未知状态';
  }
};

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleString();
};
</script>

<style scoped>
.tasks-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 112px); /* Header + Padding */
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-family: 'Source Han Serif SC', serif;
  color: var(--text-primary);
}

.split-layout {
  display: flex;
  flex: 1;
  gap: 24px;
  overflow: hidden;
}

.task-list-panel {
  width: 350px;
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  box-shadow: 0 2px 8px rgba(190, 198, 213, 0.1);
  overflow-y: auto;
  border: 1px solid var(--line-soft);
}

.task-list-item {
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s;
  border-bottom: 1px solid var(--line-soft);
}

.task-list-item:hover {
  background-color: var(--bg-base);
}

.task-list-item.active {
  background-color: var(--primary-soft);
  border-left: 4px solid var(--primary);
}

.task-name {
  font-weight: 500;
  color: var(--text-primary);
}

.task-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}

.task-detail-panel {
  flex: 1;
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  box-shadow: 0 2px 8px rgba(190, 198, 213, 0.1);
  border: 1px solid var(--line-soft);
  overflow-y: auto;
  padding: 24px;
}

.empty-detail {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100%;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line-soft);
}

.detail-header h3 {
  margin: 0;
  font-size: 20px;
  color: var(--text-primary);
}

.detail-desc {
  margin-bottom: 24px;
}

.detail-section {
  margin-bottom: 24px;
}

.detail-section h4 {
  margin-bottom: 12px;
  color: var(--text-primary);
  font-weight: 500;
  border-left: 4px solid var(--primary);
  padding-left: 8px;
}

.result-pre {
  background: var(--bg-base);
  padding: 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--line-soft);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  overflow-x: auto;
  color: var(--text-primary);
}
</style>
