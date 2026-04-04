import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import BasicLayout from '@/components/layout/BasicLayout.vue'

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    component: BasicLayout,
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('@/views/Home.vue'),
        meta: { title: '首页' }
      },
      {
        path: 'projects',
        name: 'Projects',
        component: () => import('@/views/projects/Index.vue'),
        meta: { title: '项目列表' }
      },
      {
        path: 'projects/:projectId',
        name: 'ProjectDetail',
        component: () => import('@/views/projects/Detail.vue'),
        meta: { title: '项目详情' },
        children: [
          {
            path: 'datasets',
            name: 'Datasets',
            component: () => import('@/views/projects/Datasets.vue'),
            meta: { title: '数据集' }
          },
          {
            path: 'sentiment',
            name: 'Sentiment',
            component: () => import('@/views/projects/Sentiment.vue'),
            meta: { title: '情感分析' }
          },
          {
            path: 'statistics',
            name: 'Statistics',
            component: () => import('@/views/projects/Statistics.vue'),
            meta: { title: '数据统计' }
          },
          {
            path: 'processing',
            name: 'Processing',
            component: () => import('@/views/projects/Processing.vue'),
            meta: { title: '数据处理' }
          },
          {
            path: 'tasks',
            name: 'Tasks',
            component: () => import('@/views/projects/Tasks.vue'),
            meta: { title: '任务中心' }
          },
          {
            path: 'exports',
            name: 'Exports',
            component: () => import('@/views/projects/Exports.vue'),
            meta: { title: '导出中心' }
          },
          {
            path: 'templates',
            name: 'Templates',
            component: () => import('@/views/projects/Templates.vue'),
            meta: { title: '模板中心' }
          },
          {
            path: 'settings',
            name: 'Settings',
            component: () => import('@/views/projects/Settings.vue'),
            meta: { title: '设置中心' }
          }
        ]
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach((to, _from, next) => {
  if (to.meta.title) {
    document.title = `${to.meta.title} - 数据分析工作台`
  }
  next()
})

export default router
