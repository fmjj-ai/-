<template>
  <a-layout style="min-height: 100vh">
    <a-layout-header class="app-header">
      <div class="logo">数据分析工作台</div>
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
      <a-layout-sider width="200" class="app-sider">
        <a-menu
          v-model:selectedKeys="selectedKeys"
          mode="inline"
          style="height: 100%; border-right: 0"
          @click="handleMenuClick"
        >
          <a-menu-item key="Home">首页</a-menu-item>
          <a-menu-item key="Projects">项目列表</a-menu-item>
          
          <template v-if="projectId">
            <a-menu-divider />
            <a-menu-item key="Datasets">数据集</a-menu-item>
            <a-menu-item key="Sentiment">情感分析</a-menu-item>
            <a-menu-item key="Statistics">数据统计</a-menu-item>
            <a-menu-item key="Processing">数据处理</a-menu-item>
            <a-menu-item key="Tasks">任务中心</a-menu-item>
            <a-menu-item key="Exports">导出中心</a-menu-item>
            <a-menu-item key="Templates">模板中心</a-menu-item>
            <a-menu-item key="Settings">设置中心</a-menu-item>
          </template>
        </a-menu>
      </a-layout-sider>
      <a-layout-content style="padding: 24px">
        <router-view />
      </a-layout-content>
    </a-layout>
    <GlobalTaskCenter />
  </a-layout>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, computed } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { BellOutlined } from '@ant-design/icons-vue';
import { useTaskStore } from '@/store/modules/task';
import GlobalTaskCenter from '@/components/GlobalTaskCenter.vue';

const router = useRouter();
const route = useRoute();
const taskStore = useTaskStore();
const selectedKeys = ref<string[]>([route.name as string || 'Home']);

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

.logo {
  font-size: 18px;
  font-weight: bold;
  color: var(--primary);
  font-family: 'Source Han Serif SC', serif;
}

.app-sider {
  background: var(--bg-elevated);
}
</style>
