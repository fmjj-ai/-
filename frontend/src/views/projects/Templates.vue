<template>
  <div class="templates-container">
    <a-card title="模板中心" :bordered="false" class="neumorphism-card h-full">
      <template #extra>
        <a-button type="primary">
          <template #icon><PlusOutlined /></template>
          新建模板
        </a-button>
      </template>
      
      <a-tabs v-model:activeKey="activeTab">
        <a-tab-pane key="clean" tab="清洗模板">
          <a-list :grid="{ gutter: 16, column: 3 }" :data-source="getTemplates('clean')">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-card hoverable class="template-card">
                  <template #title>
                    <span><ToolOutlined class="mr-8" />{{ item.name }}</span>
                  </template>
                  <template #extra>
                    <a-dropdown>
                      <a class="ant-dropdown-link" @click.prevent>
                        <MoreOutlined />
                      </a>
                      <template #overlay>
                        <a-menu>
                          <a-menu-item key="1">编辑</a-menu-item>
                          <a-menu-item key="2">应用到数据集</a-menu-item>
                          <a-menu-divider />
                          <a-menu-item key="3" style="color: red;">删除</a-menu-item>
                        </a-menu>
                      </template>
                    </a-dropdown>
                  </template>
                  <p class="desc">{{ item.desc }}</p>
                  <div class="meta">
                    <span>更新时间: {{ item.updatedAt }}</span>
                  </div>
                </a-card>
              </a-list-item>
            </template>
          </a-list>
        </a-tab-pane>

        <a-tab-pane key="chart" tab="图表模板">
          <a-list :grid="{ gutter: 16, column: 3 }" :data-source="getTemplates('chart')">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-card hoverable class="template-card">
                  <template #title>
                    <span><PieChartOutlined class="mr-8" />{{ item.name }}</span>
                  </template>
                  <template #extra>
                    <a-dropdown>
                      <a class="ant-dropdown-link" @click.prevent>
                        <MoreOutlined />
                      </a>
                      <template #overlay>
                        <a-menu>
                          <a-menu-item key="1">编辑</a-menu-item>
                          <a-menu-item key="2">应用到图表</a-menu-item>
                          <a-menu-divider />
                          <a-menu-item key="3" style="color: red;">删除</a-menu-item>
                        </a-menu>
                      </template>
                    </a-dropdown>
                  </template>
                  <p class="desc">{{ item.desc }}</p>
                  <div class="meta">
                    <span>更新时间: {{ item.updatedAt }}</span>
                  </div>
                </a-card>
              </a-list-item>
            </template>
          </a-list>
        </a-tab-pane>

        <a-tab-pane key="stat" tab="统计模板">
          <a-empty description="暂无统计模板" style="margin-top: 40px;" />
        </a-tab-pane>

        <a-tab-pane key="model" tab="建模模板">
          <a-empty description="暂无建模模板" style="margin-top: 40px;" />
        </a-tab-pane>

        <a-tab-pane key="export" tab="导出模板">
          <a-empty description="暂无导出模板" style="margin-top: 40px;" />
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { 
  PlusOutlined, ToolOutlined, PieChartOutlined, MoreOutlined
} from '@ant-design/icons-vue';

const activeTab = ref('clean');

const templates = ref([
  {
    id: 1,
    type: 'clean',
    name: '常规清洗模板 v1',
    desc: '删除空行，使用均值填充数值列缺失值，IQR检测异常值',
    updatedAt: '2023-10-15 14:30'
  },
  {
    id: 2,
    type: 'clean',
    name: '严格清洗',
    desc: '删除任何含有缺失值或异常值的行',
    updatedAt: '2023-10-12 09:15'
  },
  {
    id: 3,
    type: 'chart',
    name: '汇报专用柱状图',
    desc: '黑金商务色卡，隐藏网格线，显示数值标签',
    updatedAt: '2023-10-20 16:45'
  }
]);

const getTemplates = (type: string) => {
  return templates.value.filter(t => t.type === type);
};
</script>

<style scoped>
.templates-container {
  height: 100%;
}
.h-full {
  height: 100%;
}
.template-card {
  border-radius: var(--radius-md);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}
.template-card .desc {
  color: var(--text-secondary);
  font-size: 13px;
  min-height: 40px;
  margin-bottom: 12px;
}
.template-card .meta {
  font-size: 12px;
  color: var(--text-color);
  opacity: 0.6;
  border-top: 1px solid var(--border-color);
  padding-top: 8px;
}
.mr-8 {
  margin-right: 8px;
}
</style>
