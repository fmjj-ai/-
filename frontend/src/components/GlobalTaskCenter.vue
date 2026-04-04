<template>
  <a-drawer
    v-model:open="taskStore.showTaskCenter"
    title="全局任务中心"
    placement="right"
    :width="400"
    :closable="true"
    @close="taskStore.toggleTaskCenter()"
  >
    <div v-if="taskStore.tasks.length === 0" class="empty-state">
      <a-empty description="暂无任务记录" />
    </div>
    
    <div v-else class="task-list">
      <div v-for="task in taskStore.tasks" :key="task.id" class="task-item">
        <div class="task-header">
          <span class="task-name">{{ task.name || '未命名任务' }}</span>
          <a-tag :color="getStatusColor(task.status)">{{ getStatusText(task.status) }}</a-tag>
        </div>
        
        <div class="task-progress" v-if="task.status === 'running' || task.status === 'pending'">
          <a-progress :percent="task.progress || 0" size="small" :status="task.status === 'running' ? 'active' : 'normal'" />
        </div>
        
        <div class="task-meta">
          <span class="task-type">类型: {{ task.type }}</span>
          <span class="task-time">{{ formatDate(task.created_at) }}</span>
        </div>
        
        <div class="task-error" v-if="task.status === 'failed' && task.error_msg">
          <a-alert :message="task.error_msg" type="error" show-icon />
        </div>
        
        <div class="task-actions">
          <a-button type="link" danger size="small" @click="handleDelete(task.id)">删除</a-button>
          <!-- Optional: router-link to task details if it's within a project -->
        </div>
      </div>
    </div>
  </a-drawer>
</template>

<script setup lang="ts">
import { useTaskStore } from '@/store/modules/task';
import { onMounted, onUnmounted } from 'vue';
import { message } from 'ant-design-vue';

const taskStore = useTaskStore();

onMounted(() => {
  taskStore.connectSSE();
});

onUnmounted(() => {
  taskStore.disconnectSSE();
});

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
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return date.toLocaleString();
};

const handleDelete = async (taskId: string) => {
  try {
    await taskStore.deleteTask(taskId);
    message.success('任务删除成功');
  } catch (error) {
    message.error('删除任务失败');
  }
};
</script>

<style scoped>
.empty-state {
  margin-top: 60px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.task-item {
  border: 1px solid var(--line-soft);
  border-radius: var(--radius-md);
  padding: 16px;
  background-color: var(--bg-elevated);
  box-shadow: 0 2px 8px rgba(190, 198, 213, 0.1);
  transition: all 0.3s ease;
}

.task-item:hover {
  box-shadow: 0 4px 12px rgba(190, 198, 213, 0.2);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.task-name {
  font-weight: 500;
  color: var(--text-primary);
  font-size: 14px;
}

.task-progress {
  margin-bottom: 12px;
}

.task-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 12px;
}

.task-error {
  margin-bottom: 12px;
}

.task-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
