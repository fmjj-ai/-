<template>
  <div class="home">
    <!-- 头部欢迎与快捷入口 -->
    <a-row :gutter="24" class="mb-24">
      <a-col :span="16">
        <a-card :bordered="false" class="welcome-card neumorphism-card">
          <div class="welcome-content">
            <h2>欢迎来到数据分析工作台</h2>
            <p>一站式数据导入、处理、情感分析与统计建模平台</p>
            <a-space size="middle" class="mt-16">
              <a-button type="primary" size="large" @click="$router.push({ name: 'Projects' })">
                <template #icon><FolderOpenOutlined /></template>
                项目管理
              </a-button>
              <a-button size="large" @click="taskStore.toggleTaskCenter()">
                <template #icon><BellOutlined /></template>
                任务中心
              </a-button>
            </a-space>
          </div>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="快捷入口" :bordered="false" class="neumorphism-card h-full">
          <div class="shortcuts-grid">
            <div class="shortcut-item" @click="openProjectPicker('Datasets', '选择项目并进入数据导入')">
              <UploadOutlined class="shortcut-icon" />
              <span>数据导入</span>
            </div>
            <div class="shortcut-item" @click="openProjectPicker('Exports', '选择项目并进入导出中心')">
              <ExportOutlined class="shortcut-icon" />
              <span>导出中心</span>
            </div>
            <div class="shortcut-item" @click="openProjectPicker('Templates', '选择项目并进入模板中心')">
              <AppstoreOutlined class="shortcut-icon" />
              <span>模板中心</span>
            </div>
            <div class="shortcut-item" @click="openProjectPicker('Settings', '选择项目并进入项目设置')">
              <SettingOutlined class="shortcut-icon" />
              <span>全局设置</span>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 三大模块入口 -->
    <h3 class="section-title">核心功能模块</h3>
    <a-row :gutter="24" class="mb-24">
      <a-col :span="8" v-for="module in modules" :key="module.key">
        <a-card hoverable :bordered="false" class="module-card neumorphism-card" @click="handleModuleClick(module)">
          <div class="module-icon" :style="{ backgroundColor: module.color + '20', color: module.color }">
            <component :is="module.icon" />
          </div>
          <div class="module-info">
            <h4>{{ module.title }}</h4>
            <p>{{ module.desc }}</p>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 最近项目与任务状态 -->
    <a-row :gutter="24">
      <a-col :span="16">
        <a-card title="最近项目" :bordered="false" class="neumorphism-card h-full">
          <template #extra><a @click="$router.push({ name: 'Projects' })">查看全部</a></template>
          <a-list :dataSource="recentProjects" :loading="loadingProjects">
            <template #renderItem="{ item }">
              <a-list-item class="hover-list-item" @click="goToProject(item.id)">
                <a-list-item-meta :description="item.description || '暂无描述'">
                  <template #title>
                    <a>{{ item.name }}</a>
                  </template>
                </a-list-item-meta>
                <div>数据集: {{ item.dataset_count || 0 }}</div>
              </a-list-item>
            </template>
            <template #empty v-if="!loadingProjects && recentProjects.length === 0">
              <a-empty description="暂无项目，去新建一个吧" />
            </template>
          </a-list>
        </a-card>
      </a-col>
      <a-col :span="8">
        <a-card title="运行中的任务" :bordered="false" class="neumorphism-card h-full">
          <template #extra><a @click="taskStore.toggleTaskCenter()">全局任务</a></template>
          <a-list :dataSource="activeTasks" :locale="{ emptyText: '当前没有运行中的任务' }">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-list-item-meta :description="item.status">
                  <template #title>{{ item.name || item.type }}</template>
                </a-list-item-meta>
                <a-progress type="circle" :percent="Math.round((item.progress || 0) * 100)" :width="40" />
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>
  </div>

  <ProjectPickerModal
    v-model:open="pickerVisible"
    :target-route-name="pickerTargetRoute"
    :dialog-title="pickerTitle"
    default-view="card"
  />
</template>

<script setup lang="ts">
import { ref, onMounted, computed, markRaw } from 'vue';
import { useRouter } from 'vue-router';
import request from '@/utils/request';
import { useTaskStore } from '@/store/modules/task';
import ProjectPickerModal from '@/components/ProjectPickerModal.vue';
import { 
  FolderOpenOutlined, BellOutlined, UploadOutlined, ExportOutlined, 
  AppstoreOutlined, SettingOutlined, HeartOutlined, BarChartOutlined, 
  BlockOutlined 
} from '@ant-design/icons-vue';

const router = useRouter();
const taskStore = useTaskStore();

const modules = [
  {
    key: 'Sentiment',
    title: '情感分析',
    desc: '分词、停用词、SnowNLP/DeepSeek 情感打分、LDA 主题模型、词云',
    icon: markRaw(HeartOutlined),
    color: '#ff4d4f'
  },
  {
    key: 'Statistics',
    title: '数据统计分析',
    desc: '缺失异常清洗、数据概览、描述性统计、相关性矩阵、回归分析',
    icon: markRaw(BarChartOutlined),
    color: '#1890ff'
  },
  {
    key: 'Processing',
    title: '数据处理分析',
    desc: '特征编码、聚类寻优、机器学习模型对比、深度学习对比',
    icon: markRaw(BlockOutlined),
    color: '#52c41a'
  }
];

const recentProjects = ref<any[]>([]);
const loadingProjects = ref(false);
const pickerVisible = ref(false);
const pickerTargetRoute = ref('Datasets');
const pickerTitle = ref('选择项目');

const activeTasks = computed(() => {
  return taskStore.tasks.filter(t => t.status === 'running' || t.status === 'pending').slice(0, 5);
});

const fetchRecentProjects = async () => {
  loadingProjects.value = true;
  try {
    const res: any = await request.get('/projects/', { params: { limit: 5 } });
    if (res.success) {
      recentProjects.value = res.data;
    }
  } catch (e) {
    console.error('Failed to fetch recent projects', e);
  } finally {
    loadingProjects.value = false;
  }
};

const goToProject = (projectId: number) => {
  router.push({ name: 'Datasets', params: { projectId: String(projectId) } });
};

const openProjectPicker = (routeName: string, title: string) => {
  pickerTargetRoute.value = routeName;
  pickerTitle.value = title;
  pickerVisible.value = true;
};

const handleModuleClick = (module: any) => {
  openProjectPicker(module.key, `选择项目并进入${module.title}`);
};

onMounted(() => {
  fetchRecentProjects();
});
</script>

<style scoped>
.mb-24 {
  margin-bottom: 24px;
}
.mt-16 {
  margin-top: 16px;
}
.h-full {
  height: 100%;
}
.section-title {
  margin-bottom: 16px;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-color);
}

.welcome-card {
  background: linear-gradient(135deg, var(--primary-light) 0%, var(--bg-elevated) 100%);
}
.welcome-content {
  padding: 16px 8px;
}
.welcome-content h2 {
  font-size: 24px;
  margin-bottom: 8px;
  color: var(--primary);
}
.welcome-content p {
  color: var(--text-secondary);
  font-size: 16px;
}

.shortcuts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  padding: 8px;
}
.shortcut-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: var(--bg-color);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all 0.3s;
}
.shortcut-item:hover {
  background: var(--primary-light);
  color: var(--primary);
}
.shortcut-icon {
  font-size: 24px;
  margin-bottom: 8px;
  color: var(--primary);
}

.module-card {
  display: flex;
  align-items: flex-start;
  padding: 16px;
  transition: transform 0.3s, box-shadow 0.3s;
}
.module-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.1);
}
.module-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  margin-right: 16px;
  flex-shrink: 0;
}
.module-info h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  font-weight: 600;
}
.module-info p {
  margin: 0;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.5;
}

.hover-list-item {
  cursor: pointer;
  transition: background-color 0.3s;
  padding: 12px 16px;
  border-radius: var(--radius-md);
}
.hover-list-item:hover {
  background-color: var(--bg-color);
}
</style>

