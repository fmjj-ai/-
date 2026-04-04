<template>
  <div class="exports-container">
    <div class="page-header">
      <h2>导出中心</h2>
      <a-button @click="fetchArtifacts" :loading="loading">刷新</a-button>
    </div>

    <a-card class="exports-card" :bordered="false">
      <a-table
        :dataSource="artifacts"
        :columns="columns"
        :loading="loading"
        rowKey="id"
        :pagination="{ pageSize: 10 }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'name'">
            <span class="file-name">{{ record.name }}</span>
          </template>

          <template v-if="column.dataIndex === 'type'">
            <a-tag :color="getTypeColor(record.type)">{{ record.type.toUpperCase() }}</a-tag>
          </template>

          <template v-if="column.dataIndex === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>

          <template v-if="column.key === 'action'">
            <a-space>
              <a-button type="link" @click="handleDownload(record)">下载</a-button>
              <a-popconfirm
                title="确定要删除该文件吗？"
                ok-text="确定"
                cancel-text="取消"
                @confirm="handleDelete(record.id)"
              >
                <a-button type="link" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import request from '@/utils/request';
import { message } from 'ant-design-vue';

const route = useRoute();
const projectId = route.params.projectId as string;

const loading = ref(false);
const artifacts = ref<any[]>([]);

const columns = [
  {
    title: '文件名',
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: '来源模块',
    dataIndex: 'source_module',
    key: 'source_module',
  },
  {
    title: '导出类型',
    dataIndex: 'type',
    key: 'type',
  },
  {
    title: '生成时间',
    dataIndex: 'created_at',
    key: 'created_at',
    sorter: (a: any, b: any) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  },
  {
    title: '操作',
    key: 'action',
    width: 150,
  }
];

const fetchArtifacts = async () => {
  loading.value = true;
  try {
    const res: any = await request.get('/artifacts/', { params: { project_id: projectId } });
    if (res.success) {
      artifacts.value = res.data;
    }
  } catch (error) {
    console.error('Failed to fetch artifacts', error);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchArtifacts();
});

const handleDownload = (record: any) => {
  // Use window.open or create an anchor to download
  const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
  const downloadUrl = `${baseURL}/artifacts/${record.id}/download`;
  window.open(downloadUrl, '_blank');
};

const handleDelete = async (id: number) => {
  try {
    const res: any = await request.delete(`/artifacts/${id}`);
    if (res.success) {
      message.success('删除成功');
      artifacts.value = artifacts.value.filter(item => item.id !== id);
    }
  } catch (error) {
    message.error('删除失败');
  }
};

const getTypeColor = (type: string) => {
  switch (type.toLowerCase()) {
    case 'csv': return 'green';
    case 'pdf': return 'red';
    case 'png': 
    case 'svg': return 'blue';
    default: return 'default';
  }
};

const formatDate = (dateStr: string) => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleString();
};
</script>

<style scoped>
.exports-container {
  display: flex;
  flex-direction: column;
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

.exports-card {
  background: var(--bg-elevated);
  border-radius: var(--radius-lg);
  box-shadow: 0 2px 8px rgba(190, 198, 213, 0.1);
  border: 1px solid var(--line-soft);
}

.file-name {
  font-weight: 500;
  color: var(--text-primary);
}
</style>
