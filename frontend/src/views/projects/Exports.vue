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
              <a-button type="link" @click="handlePreview(record)" v-if="canPreview(record.type)">预览</a-button>
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

    <!-- Preview Modal -->
    <a-modal
      v-model:visible="previewVisible"
      title="文件预览"
      width="80%"
      style="top: 20px"
      :footer="null"
      @cancel="closePreview"
    >
      <div v-if="previewLoading" style="text-align: center; padding: 50px;">
        <a-spin size="large" />
      </div>
      <div v-else-if="previewType === 'image'" style="text-align: center;">
        <img :src="previewUrl" style="max-width: 100%; max-height: 70vh;" />
      </div>
      <div v-else-if="previewType === 'iframe'" style="height: 70vh;">
        <iframe :src="previewUrl" width="100%" height="100%" frameborder="0"></iframe>
      </div>
      <div v-else-if="previewType === 'text'" style="height: 70vh; overflow: auto; background: var(--bg-color); padding: 16px; border-radius: 4px;">
        <pre style="white-space: pre-wrap; font-family: monospace; margin: 0;">{{ previewText }}</pre>
      </div>
      <div v-else-if="previewType === 'csv'" class="csv-preview">
        <div class="csv-preview-summary">
          <span>数据行：{{ previewCsvMeta.rowCount }}</span>
          <span>列数：{{ previewCsvMeta.columnCount }}</span>
        </div>
        <a-empty
          v-if="previewCsvMeta.columnCount === 0"
          description="CSV 文件没有可展示的数据"
        />
        <a-table
          v-else
          class="csv-preview-table"
          :columns="previewCsvColumns"
          :data-source="previewCsvRows"
          rowKey="__rowKey"
          size="small"
          :pagination="{
            pageSize: 20,
            showSizeChanger: true,
            pageSizeOptions: ['20', '50', '100']
          }"
          :scroll="{ x: 'max-content', y: 520 }"
        />
      </div>
      <div v-else style="text-align: center; padding: 50px;">
        <p>该文件类型暂不支持预览，请下载后查看。</p>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import request from '@/utils/request';
import { message } from 'ant-design-vue';

type PreviewType = '' | 'image' | 'iframe' | 'text' | 'csv' | 'unsupported';

const route = useRoute();
const projectId = route.params.projectId as string;

const loading = ref(false);
const artifacts = ref<any[]>([]);

const previewVisible = ref(false);
const previewLoading = ref(false);
const previewType = ref<PreviewType>('');
const previewUrl = ref('');
const previewText = ref('');
const previewCsvColumns = ref<any[]>([]);
const previewCsvRows = ref<any[]>([]);
const previewCsvMeta = ref({
  rowCount: 0,
  columnCount: 0,
});

const columns = [
  {
    title: '文件名',
    dataIndex: 'name',
    key: 'name',
  },
  {
    title: '来源任务',
    dataIndex: 'task_name',
    key: 'task_name',
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
    width: 200,
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

const canPreview = (type: string) => {
  const t = type.toLowerCase();
  return ['markdown', 'md', 'pdf', 'html', 'png', 'svg', 'jpg', 'jpeg', 'txt', 'json', 'csv'].includes(t);
};

const resetPreviewState = () => {
  previewType.value = '';
  previewText.value = '';
  previewCsvColumns.value = [];
  previewCsvRows.value = [];
  previewCsvMeta.value = {
    rowCount: 0,
    columnCount: 0,
  };
};

const parseCsvText = (source: string) => {
  const text = source.charCodeAt(0) === 0xfeff ? source.slice(1) : source;
  const rows: string[][] = [];
  let currentRow: string[] = [];
  let currentCell = '';
  let inQuotes = false;

  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const nextChar = text[index + 1];

    if (char === '\r') {
      continue;
    }

    if (inQuotes) {
      if (char === '"') {
        if (nextChar === '"') {
          currentCell += '"';
          index += 1;
        } else {
          inQuotes = false;
        }
      } else {
        currentCell += char;
      }
      continue;
    }

    if (char === '"') {
      inQuotes = true;
      continue;
    }

    if (char === ',') {
      currentRow.push(currentCell);
      currentCell = '';
      continue;
    }

    if (char === '\n') {
      currentRow.push(currentCell);
      rows.push(currentRow);
      currentRow = [];
      currentCell = '';
      continue;
    }

    currentCell += char;
  }

  if (currentCell.length > 0 || currentRow.length > 0) {
    currentRow.push(currentCell);
    rows.push(currentRow);
  }

  return rows.filter((row) => row.some((cell) => String(cell).trim() !== ''));
};

const buildCsvPreview = (text: string) => {
  const parsedRows = parseCsvText(text);
  if (!parsedRows.length) {
    return {
      columns: [],
      rows: [],
      rowCount: 0,
      columnCount: 0,
    };
  }

  const headerRow = parsedRows[0];
  const dataRows = parsedRows.slice(1);
  const columnCount = parsedRows.reduce((max, row) => Math.max(max, row.length), 0);
  const titleUsage = new Map<string, number>();

  const columns = Array.from({ length: columnCount }, (_, index) => {
    const rawTitle = String(headerRow[index] ?? '').trim();
    const baseTitle = rawTitle || `列${index + 1}`;
    const usedCount = titleUsage.get(baseTitle) ?? 0;
    titleUsage.set(baseTitle, usedCount + 1);

    return {
      title: usedCount === 0 ? baseTitle : `${baseTitle} (${usedCount + 1})`,
      dataIndex: `column_${index}`,
      key: `column_${index}`,
      width: 220,
    };
  });

  const rows = dataRows.map((row, rowIndex) => {
    const item: Record<string, string | number> = {
      __rowKey: rowIndex + 1,
    };

    for (let index = 0; index < columnCount; index += 1) {
      item[`column_${index}`] = row[index] ?? '';
    }

    return item;
  });

  return {
    columns,
    rows,
    rowCount: rows.length,
    columnCount,
  };
};

const handlePreview = async (record: any) => {
  const t = record.type.toLowerCase();
  const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
  const url = `${baseURL}/artifacts/${record.id}/preview`;
  
  previewVisible.value = true;
  previewLoading.value = true;
  previewUrl.value = url;
  resetPreviewState();
  
  if (['png', 'svg', 'jpg', 'jpeg'].includes(t)) {
    previewType.value = 'image';
    previewLoading.value = false;
  } else if (['pdf', 'html'].includes(t)) {
    previewType.value = 'iframe';
    previewLoading.value = false;
  } else if (t === 'csv') {
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`CSV 预览加载失败: ${response.status}`);
      }

      const text = await response.text();
      const preview = buildCsvPreview(text);
      previewType.value = 'csv';
      previewCsvColumns.value = preview.columns;
      previewCsvRows.value = preview.rows;
      previewCsvMeta.value = {
        rowCount: preview.rowCount,
        columnCount: preview.columnCount,
      };
    } catch (e) {
      previewType.value = 'text';
      previewText.value = 'CSV 预览加载失败';
    } finally {
      previewLoading.value = false;
    }
  } else if (['markdown', 'md', 'txt', 'json'].includes(t)) {
    previewType.value = 'text';
    try {
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`文本预览加载失败: ${response.status}`);
      }

      const text = await response.text();
      previewText.value = text;
    } catch (e) {
      previewText.value = '预览加载失败';
    } finally {
      previewLoading.value = false;
    }
  } else {
    previewType.value = 'unsupported';
    previewLoading.value = false;
  }
};

const closePreview = () => {
  previewVisible.value = false;
  previewUrl.value = '';
  resetPreviewState();
};

const getFileExtension = (record: any) => {
  const fromPath = String(record?.file_path || '').split(/[\\/]/).pop() || '';
  const dotIndex = fromPath.lastIndexOf('.');
  if (dotIndex > -1 && dotIndex < fromPath.length - 1) {
    return fromPath.slice(dotIndex).toLowerCase();
  }

  const type = String(record?.type || '').toLowerCase();
  const extMap: Record<string, string> = {
    html: '.html',
    markdown: '.md',
    md: '.md',
    csv: '.csv',
    json: '.json',
    txt: '.txt',
    pdf: '.pdf',
    png: '.png',
    svg: '.svg',
    jpg: '.jpg',
    jpeg: '.jpeg'
  };
  return extMap[type] || '';
};

const getDownloadName = (record: any) => {
  const baseName = String(record?.name || 'download').trim() || 'download';
  if (/\.[^./\\]+$/.test(baseName)) {
    return baseName;
  }
  return `${baseName}${getFileExtension(record)}`;
};

const handleDownload = async (record: any) => {
  const baseURL = import.meta.env.VITE_API_BASE_URL || '/api/v1';
  const downloadUrl = `${baseURL}/artifacts/${record.id}/download`;
  try {
    const response = await fetch(downloadUrl);
    if (!response.ok) {
      throw new Error(`下载失败: ${response.status}`);
    }

    const blob = await response.blob();
    const objectUrl = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = objectUrl;
    link.download = getDownloadName(record);
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(objectUrl);
  } catch (error) {
    console.error('Download failed', error);
    message.error('下载失败');
  }
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

.csv-preview {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.csv-preview-summary {
  color: var(--text-secondary);
  font-size: 13px;
}

.csv-preview-summary span + span {
  margin-left: 16px;
}

.csv-preview-table :deep(.ant-table-cell) {
  white-space: pre-wrap;
  word-break: break-word;
  vertical-align: top;
}
</style>
