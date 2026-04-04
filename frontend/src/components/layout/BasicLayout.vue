<template>
  <a-layout style="min-height: 100vh">
    <a-layout-header class="app-header">
      <div class="header-left">
        <div class="logo">数据分析工作台</div>
        <div class="collapse-btn" @click="collapsed = !collapsed">
          <MenuFoldOutlined v-if="!collapsed" />
          <MenuUnfoldOutlined v-else />
        </div>
      </div>
      <div class="header-right">
        <!-- 全局任务中心触发按钮 -->
        <a-badge :count="taskStore.unreadCount" :overflow-count="99">
          <a-button type="text" @click="taskStore.toggleTaskCenter()">
            <template #icon><BellOutlined /></template>
            任务中心
          </a-button>
        </a-badge>
      </div>
    </a-layout-header>
    <a-layout>
      <a-layout-sider 
        v-model:collapsed="collapsed" 
        :width="200" 
        :collapsedWidth="80"
        class="app-sider"
        collapsible
        :trigger="null"
      >
        <a-menu
          v-model:selectedKeys="selectedKeys"
          mode="inline"
          style="height: 100%; border-right: 0"
          @click="handleMenuClick"
        >
          <a-menu-item key="Home">
            <HomeOutlined />
            <span>首页</span>
          </a-menu-item>
          <a-menu-item key="Projects">
            <ProjectOutlined />
            <span>项目列表</span>
          </a-menu-item>
          
          <template v-if="projectId">
            <a-menu-divider />
            <a-menu-item key="Datasets">
              <DatabaseOutlined />
              <span>数据集</span>
            </a-menu-item>
            <a-menu-item key="Sentiment">
              <HeartOutlined />
              <span>情感分析</span>
            </a-menu-item>
            <a-menu-item key="Statistics">
              <BarChartOutlined />
              <span>数据统计</span>
            </a-menu-item>
            <a-menu-item key="Processing">
              <BlockOutlined />
              <span>数据处理</span>
            </a-menu-item>
            <a-menu-item key="Tasks">
              <CheckSquareOutlined />
              <span>任务记录</span>
            </a-menu-item>
            <a-menu-item key="Exports">
              <ExportOutlined />
              <span>导出中心</span>
            </a-menu-item>
            <a-menu-item key="Templates">
              <AppstoreOutlined />
              <span>模板中心</span>
            </a-menu-item>
            <a-menu-item key="Settings">
              <SettingOutlined />
              <span>项目设置</span>
            </a-menu-item>
          </template>
        </a-menu>
      </a-layout-sider>
      <a-layout-content class="app-content">
        <router-view />
      </a-layout-content>
    </a-layout>
    <GlobalTaskCenter />
  </a-layout>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { 
  BellOutlined, MenuFoldOutlined, MenuUnfoldOutlined, 
  HomeOutlined, ProjectOutlined, DatabaseOutlined, 
  HeartOutlined, BarChartOutlined, BlockOutlined, 
  CheckSquareOutlined, ExportOutlined, AppstoreOutlined, 
  SettingOutlined 
} from '@ant-design/icons-vue';
import { useTaskStore } from '@/store/modules/task';
import GlobalTaskCenter from '@/components/GlobalTaskCenter.vue';

const router = useRouter();
const route = useRoute();
const taskStore = useTaskStore();
const selectedKeys = ref<string[]>([route.name as string || 'Home']);
const collapsed = ref<boolean>(false);

const projectId = computed(() => route.params.projectId as string | undefined);

onMounted(() => {
  taskStore.connectSSE();
});

watch(
  () => route.name,
  (name) => {
    if (name) {
      selectedKeys.value = [name as string];
    }
  }
);

const handleMenuClick = ({ key }: { key: string }) => {
  if (projectId.value && ['Datasets', 'Sentiment', 'Statistics', 'Processing', 'Tasks', 'Exports', 'Templates', 'Settings'].includes(key)) {
    router.push({ name: key, params: { projectId: projectId.value } });
  } else {
    router.push({ name: key });
  }
};
</script>

<style scoped>
.app-header {
  background: var(--bg-elevated);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(190, 198, 213, 0.2);
  z-index: 10;
}

.header-left {
  display: flex;
  align-items: center;
}

.logo {
  font-size: 18px;
  font-weight: bold;
  color: var(--primary);
  font-family: 'Source Han Serif SC', serif;
  margin-right: 24px;
}

.collapse-btn {
  font-size: 18px;
  cursor: pointer;
  transition: color 0.3s;
  color: var(--text-color);
}

.collapse-btn:hover {
  color: var(--primary);
}

.app-sider {
  background: var(--bg-elevated);
  box-shadow: 2px 0 8px rgba(190, 198, 213, 0.1);
  z-index: 9;
}

.app-content {
  padding: 24px;
  overflow-y: auto;
  background-color: var(--bg-color);
}
</style>
