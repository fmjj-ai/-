<template>
  <a-layout class="app-shell">
    <a-layout-header class="app-header">
      <div class="header-left">
        <div class="logo" @click="router.push({ name: 'Home' })">
          <span class="logo-mark" aria-hidden="true">墨</span>
          <span class="logo-text">数据分析工作台</span>
        </div>
        <div class="collapse-btn" @click="collapsed = !collapsed" :title="collapsed ? '展开' : '折叠'">
          <MenuFoldOutlined v-if="!collapsed" />
          <MenuUnfoldOutlined v-else />
        </div>
      </div>
      <div class="header-right">
        <a-badge :count="taskStore.unreadCount" :overflow-count="99">
          <a-button type="text" class="task-btn" @click="taskStore.toggleTaskCenter()">
            <template #icon><BellOutlined /></template>
            任务中心
          </a-button>
        </a-badge>
      </div>
    </a-layout-header>
    <a-layout class="app-body">
      <a-layout-sider
        v-model:collapsed="collapsed"
        :width="220"
        :collapsedWidth="72"
        class="app-sider"
        collapsible
        :trigger="null"
      >
        <div class="sider-inner">
          <a-menu
            v-model:selectedKeys="selectedKeys"
            mode="inline"
            class="app-menu"
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
          <div v-if="!collapsed" class="sider-foot">
            <span class="foot-glyph">·</span>
            <span class="foot-text">山高水长 · 数以观之</span>
          </div>
        </div>
      </a-layout-sider>

      <a-layout-content class="app-content-shell">
        <div class="app-content" ref="contentRef">
          <div class="app-content-inner" ref="contentInnerRef">
            <router-view v-slot="{ Component, route: r }">
              <transition name="ink-page" mode="out-in" appear>
                <!-- 用 div 包裹，保证 transition 始终是单根；
                     这样即使路由组件是多根模板也能稳定渲染 -->
                <div :key="r.fullPath" class="route-frame">
                  <component :is="Component" />
                </div>
              </transition>
            </router-view>
          </div>
        </div>
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
import { useProjectStore } from '@/store/modules/project';
import GlobalTaskCenter from '@/components/GlobalTaskCenter.vue';
import { useSpringScroll } from '@/composables/useSpringScroll';

const router = useRouter();
const route = useRoute();
const taskStore = useTaskStore();
const projectStore = useProjectStore();
const selectedKeys = ref<string[]>([route.name as string || 'Home']);
const collapsed = ref<boolean>(false);

/* 内容区滚动容器（原生 div） + 内层（用于边缘弹性形变） */
const contentRef = ref<HTMLElement | null>(null);
const contentInnerRef = ref<HTMLElement | null>(null);

useSpringScroll(contentRef, contentInnerRef, {
  stiffness: 0.10,
  wheelMultiplier: 0.9,
  bounceMax: 70,
});

const projectId = computed(() => {
  const routeProjectId = route.params.projectId as string | undefined;
  if (routeProjectId) {
    return routeProjectId;
  }
  return projectStore.currentProjectId || undefined;
});

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

watch(
  () => route.params.projectId,
  (value) => {
    if (value) {
      projectStore.setCurrentProject(String(value));
    }
  },
  { immediate: true }
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
.app-shell {
  min-height: 100vh;
  background: transparent;
}

/* —— 顶栏：磨砂玻璃 —— */
.app-header {
  position: sticky;
  top: 0;
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 60px;
  line-height: 60px;
  background: var(--bg-glass) !important;
  backdrop-filter: blur(18px) saturate(140%);
  -webkit-backdrop-filter: blur(18px) saturate(140%);
  border-bottom: 1px solid var(--line-soft);
}
.app-header::after {
  content: '';
  position: absolute;
  left: 0; right: 0; bottom: -1px;
  height: 1px;
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(74, 82, 96, 0.18) 30%,
    rgba(74, 82, 96, 0.18) 70%,
    transparent 100%);
  pointer-events: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 18px;
}

.logo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  user-select: none;
  transition: opacity 0.2s var(--ease-ink);
}
.logo:hover { opacity: 0.85; }
.logo-mark {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-serif);
  font-size: 18px;
  color: #fff;
  background:
    radial-gradient(circle at 30% 30%, #4a5260 0%, #2d3239 70%, #1a1d22 100%);
  box-shadow:
    0 4px 12px -4px rgba(45, 50, 57, 0.5),
    inset 0 -2px 4px rgba(0, 0, 0, 0.3),
    inset 0 1px 2px rgba(255, 255, 255, 0.1);
}
.logo-text {
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: var(--ink-1);
}

.collapse-btn {
  font-size: 16px;
  cursor: pointer;
  color: var(--text-secondary);
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.25s var(--ease-ink);
}
.collapse-btn:hover {
  color: var(--primary);
  background: var(--dai-soft);
}

.header-right :deep(.task-btn) { color: var(--text-secondary); }
.header-right :deep(.task-btn):hover {
  background: var(--dai-soft) !important;
  color: var(--primary) !important;
}

/* —— 主体 —— */
.app-body { background: transparent; }

/* —— 侧栏：仿宣纸卷轴 —— */
.app-sider {
  background: rgba(255, 253, 248, 0.55) !important;
  backdrop-filter: blur(14px) saturate(130%);
  -webkit-backdrop-filter: blur(14px) saturate(130%);
  border-right: 1px solid var(--line-soft);
  z-index: 9;
  position: relative;
}
.app-sider::before {
  content: '';
  position: absolute;
  top: 0; bottom: 0; right: 0;
  width: 2px;
  background: linear-gradient(180deg,
    transparent 0%,
    rgba(74, 82, 96, 0.08) 12%,
    rgba(74, 82, 96, 0.18) 50%,
    rgba(74, 82, 96, 0.08) 88%,
    transparent 100%);
  pointer-events: none;
}
.sider-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding-top: 12px;
}
.app-menu {
  flex: 1;
  border-inline-end: 0 !important;
  background: transparent !important;
}
.sider-foot {
  padding: 16px 18px 22px;
  font-family: var(--font-serif);
  font-size: 12px;
  color: var(--text-muted);
  letter-spacing: 0.18em;
  text-align: center;
  border-top: 1px dashed var(--line-soft);
}
.foot-glyph {
  display: inline-block;
  margin-right: 6px;
  color: var(--vermilion);
  transform: scale(1.6) translateY(-1px);
}

/* —— 内容区：滚动 + 弹性形变 —— */
.app-content-shell {
  /* a-layout-content 自身只占位，不滚动；滚动交给内部 .app-content */
  height: calc(100vh - 60px);
  overflow: hidden;
  position: relative;
}
.app-content {
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
  scroll-behavior: auto;
}
.app-content-inner {
  padding: 28px 32px 64px;
  min-height: 100%;
  will-change: transform;
}
.route-frame {
  /* transition 包装层：作为单根挂载点，子元素自然填充 */
  display: block;
  width: 100%;
}

/* —— 路由切换：墨色淡入 —— */
.ink-page-enter-active,
.ink-page-leave-active {
  transition: opacity 0.45s var(--ease-ink), transform 0.45s var(--ease-ink), filter 0.45s var(--ease-ink);
}
.ink-page-enter-from {
  opacity: 0;
  transform: translateY(12px);
  filter: blur(4px);
}
.ink-page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
  filter: blur(2px);
}
</style>
