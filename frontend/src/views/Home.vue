<template>
  <div class="home">
    <ProjectPickerModal
      v-model:open="pickerVisible"
      :target-route-name="pickerTargetRoute"
      :dialog-title="pickerTitle"
      default-view="card"
    />

    <!-- ========= 卷首：欢迎语 + 快捷入口 ========= -->
    <InkReveal :duration="1200" :displacement-from="36">
      <a-row :gutter="24" class="row-mb">
        <a-col :xs="24" :md="16">
          <section class="welcome-scroll">
            <div class="seal" aria-hidden="true">
              <span>数</span>
            </div>
            <div class="welcome-body">
              <p class="kicker">SOLO · DATA STUDIO</p>
              <h1 class="welcome-title">
                <span class="ch" v-for="(c, i) in titleChars" :key="i" :style="{ animationDelay: `${i * 0.06}s` }">{{ c }}</span>
              </h1>
              <p class="subtitle">观古今之数 · 知天下之理 — 数据导入、处理、情感建模与统计分析的一站式画卷</p>
              <a-space size="middle" class="welcome-actions">
                <a-button type="primary" size="large" @click="$router.push({ name: 'Projects' })">
                  <template #icon><FolderOpenOutlined /></template>
                  打开项目
                </a-button>
                <a-button size="large" @click="taskStore.toggleTaskCenter()">
                  <template #icon><BellOutlined /></template>
                  任务中心
                </a-button>
              </a-space>
            </div>
            <!-- 装饰性墨笔笔触 -->
            <svg class="brush" viewBox="0 0 220 60" aria-hidden="true">
              <path d="M5,40 C40,15 80,55 120,30 C160,8 190,42 215,25"
                stroke="rgba(45,50,57,0.55)" stroke-width="2" stroke-linecap="round" fill="none">
                <animate attributeName="stroke-dasharray" from="0,500" to="500,0" dur="1.6s" fill="freeze" />
              </path>
            </svg>
          </section>
        </a-col>
        <a-col :xs="24" :md="8">
          <a-card title="快捷入口" :bordered="false" class="card-shortcuts h-full">
            <div class="shortcuts-grid">
              <button class="shortcut-item" @click="openProjectPicker('Datasets', '选择项目并进入数据导入')">
                <UploadOutlined class="shortcut-icon" />
                <span>数据导入</span>
              </button>
              <button class="shortcut-item" @click="openProjectPicker('Exports', '选择项目并进入导出中心')">
                <ExportOutlined class="shortcut-icon" />
                <span>导出中心</span>
              </button>
              <button class="shortcut-item" @click="openProjectPicker('Templates', '选择项目并进入模板中心')">
                <AppstoreOutlined class="shortcut-icon" />
                <span>模板中心</span>
              </button>
              <button class="shortcut-item" @click="openProjectPicker('Settings', '选择项目并进入项目设置')">
                <SettingOutlined class="shortcut-icon" />
                <span>全局设置</span>
              </button>
            </div>
          </a-card>
        </a-col>
      </a-row>
    </InkReveal>

    <!-- ========= 三大模块 ========= -->
    <InkReveal :delay="160" :duration="1000" :displacement-from="24">
      <h3 class="section-title">
        <span class="title-rune">壹</span>
        <span class="title-text">核心功能模块</span>
        <span class="title-line" />
      </h3>
      <a-row :gutter="24" class="row-mb">
        <a-col :xs="24" :md="8" v-for="m in modules" :key="m.key">
          <a-card hoverable :bordered="false" class="module-card" @click="handleModuleClick(m)">
            <div class="module-glyph" :style="{ '--m-color': m.color }">
              <component :is="m.icon" />
            </div>
            <div class="module-info">
              <h4>{{ m.title }}</h4>
              <p>{{ m.desc }}</p>
            </div>
            <span class="module-arrow" aria-hidden="true">→</span>
          </a-card>
        </a-col>
      </a-row>
    </InkReveal>

    <!-- ========= 最近项目 + 运行任务 ========= -->
    <InkReveal :delay="280" :duration="900" :displacement-from="20">
      <h3 class="section-title">
        <span class="title-rune">贰</span>
        <span class="title-text">近期动向</span>
        <span class="title-line" />
      </h3>
      <a-row :gutter="24">
        <a-col :xs="24" :md="16">
          <a-card title="最近项目" :bordered="false" class="h-full">
            <template #extra><a @click="$router.push({ name: 'Projects' })">查看全部</a></template>
            <a-list :dataSource="recentProjects" :loading="loadingProjects">
              <template #renderItem="{ item }">
                <a-list-item class="hover-list-item" @click="goToProject(item.id)">
                  <a-list-item-meta :description="item.description || '暂无描述'">
                    <template #title>
                      <a>{{ item.name }}</a>
                    </template>
                  </a-list-item-meta>
                  <div class="meta-tag">数据集 · {{ item.dataset_count || 0 }}</div>
                </a-list-item>
              </template>
              <template #empty v-if="!loadingProjects && recentProjects.length === 0">
                <a-empty description="暂无项目，去新建一个吧" />
              </template>
            </a-list>
          </a-card>
        </a-col>
        <a-col :xs="24" :md="8">
          <a-card title="运行中的任务" :bordered="false" class="h-full">
            <template #extra><a @click="taskStore.toggleTaskCenter()">全局任务</a></template>
            <a-list :dataSource="activeTasks" :locale="{ emptyText: '当前没有运行中的任务' }">
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta :description="item.status">
                    <template #title>{{ item.name || item.type }}</template>
                  </a-list-item-meta>
                  <a-progress type="circle" :percent="Math.round((item.progress || 0) * 100)" :size="40" />
                </a-list-item>
              </template>
            </a-list>
          </a-card>
        </a-col>
      </a-row>
    </InkReveal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, markRaw } from 'vue';
import { useRouter } from 'vue-router';
import request from '@/utils/request';
import { useTaskStore } from '@/store/modules/task';
import ProjectPickerModal from '@/components/ProjectPickerModal.vue';
import InkReveal from '@/components/effects/InkReveal.vue';
import {
  FolderOpenOutlined, BellOutlined, UploadOutlined, ExportOutlined,
  AppstoreOutlined, SettingOutlined, HeartOutlined, BarChartOutlined,
  BlockOutlined
} from '@ant-design/icons-vue';

const router = useRouter();
const taskStore = useTaskStore();

/* 标题逐字"书写"动画使用 */
const titleChars = '欢迎来到数据分析工作台'.split('');

const modules = [
  {
    key: 'Sentiment',
    title: '情感分析',
    desc: '分词 · 停用词 · SnowNLP / DeepSeek 打分 · LDA 主题 · 词云',
    icon: markRaw(HeartOutlined),
    color: '#c75450',  /* 朱砂 */
  },
  {
    key: 'Statistics',
    title: '数据统计分析',
    desc: '清洗异常 · 描述性统计 · 相关性矩阵 · 回归分析',
    icon: markRaw(BarChartOutlined),
    color: '#5a7a8c',  /* 远山黛 */
  },
  {
    key: 'Processing',
    title: '数据处理分析',
    desc: '特征编码 · 聚类寻优 · 机器学习与深度学习模型对比',
    icon: markRaw(BlockOutlined),
    color: '#6fa287',  /* 青瓷 */
  },
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

const handleModuleClick = (m: any) => {
  openProjectPicker(m.key, `选择项目并进入${m.title}`);
};

onMounted(() => {
  fetchRecentProjects();
});
</script>

<style scoped>
.home {
  max-width: 1280px;
  margin: 0 auto;
}
.row-mb { margin-bottom: 28px; }
.h-full { height: 100%; }

/* ========= 卷首 ========= */
.welcome-scroll {
  position: relative;
  height: 100%;
  min-height: 220px;
  padding: 32px 36px 28px;
  border-radius: var(--radius-lg);
  background:
    linear-gradient(135deg,
      rgba(255, 253, 248, 0.92) 0%,
      rgba(245, 240, 230, 0.78) 60%,
      rgba(180, 199, 217, 0.32) 100%);
  border: 1px solid var(--line-soft);
  box-shadow: var(--shadow-paper);
  overflow: hidden;
  isolation: isolate;
}
.welcome-scroll::before {
  content: '';
  position: absolute;
  inset: -20% -20% auto auto;
  width: 60%;
  height: 70%;
  background:
    radial-gradient(ellipse at 70% 30%, rgba(74, 82, 96, 0.10), transparent 60%),
    radial-gradient(ellipse at 60% 50%, rgba(124, 151, 184, 0.18), transparent 70%);
  filter: blur(2px);
  z-index: -1;
  pointer-events: none;
}
.seal {
  position: absolute;
  top: 28px; right: 32px;
  width: 48px; height: 48px;
  border: 2px solid var(--vermilion);
  border-radius: 6px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: var(--font-serif);
  font-size: 22px;
  color: var(--vermilion);
  background: rgba(199, 84, 80, 0.06);
  transform: rotate(-3deg);
  user-select: none;
}
.seal::after {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 4px;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='80' height='80'><filter id='r'><feTurbulence baseFrequency='1.3' numOctaves='2' seed='5'/><feColorMatrix values='0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 0.6 0'/></filter><rect width='100%25' height='100%25' filter='url(%23r)' opacity='0.6'/></svg>");
  mix-blend-mode: screen;
  opacity: 0.8;
  pointer-events: none;
}

.welcome-body { max-width: 70%; }
.kicker {
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.32em;
  color: var(--text-muted);
  margin-bottom: 6px;
}
.welcome-title {
  font-family: var(--font-serif);
  font-size: 34px;
  font-weight: 500;
  letter-spacing: 0.06em;
  color: var(--ink-1);
  margin: 0 0 12px;
  line-height: 1.25;
}
.welcome-title .ch {
  display: inline-block;
  opacity: 0;
  transform: translateY(10px);
  filter: blur(3px);
  animation: ch-write 0.8s var(--ease-ink) forwards;
}
@keyframes ch-write {
  to { opacity: 1; transform: translateY(0); filter: blur(0); }
}
.subtitle {
  font-family: var(--font-serif);
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 18px;
  letter-spacing: 0.04em;
}
.welcome-actions { margin-top: 4px; }

.brush {
  position: absolute;
  bottom: 14px; left: 36px;
  width: 220px; height: 60px;
  opacity: 0.55;
  pointer-events: none;
}

/* ========= 快捷入口 ========= */
.card-shortcuts :deep(.ant-card-body) { padding: 16px; }
.shortcuts-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.shortcut-item {
  appearance: none;
  border: 1px solid var(--line-soft);
  background: rgba(255, 253, 248, 0.6);
  border-radius: var(--radius-md);
  padding: 18px 12px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-family: var(--font-serif);
  font-size: 13px;
  color: var(--text-secondary);
  transition: all 0.3s var(--ease-ink);
}
.shortcut-item:hover {
  background: var(--bg-elevated);
  border-color: var(--primary);
  color: var(--primary);
  transform: translateY(-2px);
  box-shadow: var(--shadow-paper);
}
.shortcut-icon { font-size: 22px; color: var(--primary); }
.shortcut-item:hover .shortcut-icon { color: var(--primary-hover); }

/* ========= 段落标题 ========= */
.section-title {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 0 0 18px;
  font-family: var(--font-serif);
  font-size: 18px;
  font-weight: 500;
  color: var(--ink-1);
  letter-spacing: 0.06em;
}
.title-rune {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px; height: 28px;
  border: 1px solid var(--line-strong);
  border-radius: 6px;
  font-size: 13px;
  color: var(--vermilion);
  background: rgba(199, 84, 80, 0.06);
}
.title-line {
  flex: 1;
  height: 1px;
  background: linear-gradient(90deg, var(--line-strong), transparent 80%);
}

/* ========= 模块卡 ========= */
.module-card {
  position: relative;
  cursor: pointer;
  overflow: hidden;
}
.module-card :deep(.ant-card-body) {
  padding: 22px 22px 20px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.module-card::before {
  content: '';
  position: absolute;
  left: 0; top: 14%; bottom: 14%;
  width: 3px;
  background: linear-gradient(180deg, transparent, var(--m-color, var(--primary)) 50%, transparent);
  opacity: 0.55;
  border-radius: 2px;
}
.module-glyph {
  width: 52px; height: 52px;
  border-radius: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
  color: var(--m-color);
  background:
    radial-gradient(circle at 30% 30%, color-mix(in srgb, var(--m-color) 22%, transparent), transparent 70%),
    rgba(255, 253, 248, 0.6);
  border: 1px solid color-mix(in srgb, var(--m-color) 25%, transparent);
  box-shadow: 0 6px 18px -8px color-mix(in srgb, var(--m-color) 50%, transparent);
}
.module-info { flex: 1; min-width: 0; }
.module-info h4 {
  margin: 0 0 6px;
  font-family: var(--font-serif);
  font-size: 16px;
  color: var(--ink-1);
  letter-spacing: 0.04em;
}
.module-info p {
  margin: 0;
  font-size: 12.5px;
  line-height: 1.7;
  color: var(--text-secondary);
}
.module-arrow {
  position: absolute;
  right: 22px; bottom: 18px;
  font-size: 18px;
  color: var(--text-muted);
  opacity: 0;
  transform: translateX(-8px);
  transition: all 0.4s var(--ease-ink);
}
.module-card:hover .module-arrow {
  opacity: 1;
  transform: translateX(0);
  color: var(--m-color);
}

/* ========= 列表 ========= */
.hover-list-item {
  cursor: pointer;
  transition: background-color 0.3s var(--ease-ink);
  padding: 12px 16px;
  border-radius: var(--radius-sm);
}
.hover-list-item:hover { background-color: var(--dai-soft); }
.meta-tag {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-muted);
  padding: 2px 10px;
  border: 1px solid var(--line-soft);
  border-radius: 999px;
  background: rgba(255, 253, 248, 0.6);
}
</style>

