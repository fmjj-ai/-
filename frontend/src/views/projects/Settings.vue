<template>
  <div class="settings-container">
    <a-card title="设置中心" :bordered="false" class="neumorphism-card h-full">
      <a-tabs v-model:activeKey="activeTab" tab-position="left">
        <!-- 模型与 API -->
        <a-tab-pane key="api" tab="模型与 API">
          <a-form layout="vertical">
            <a-form-item label="DeepSeek API Key">
              <a-input-password v-model:value="settings.deepseekApiKey" placeholder="输入 API Key" />
              <div class="form-hint">用于大模型情感分析与文本解读</div>
            </a-form-item>
            <a-form-item label="允许数据外发">
              <a-switch v-model:checked="settings.allowDataExport" />
              <div class="form-hint warning-hint">开启后，系统在调用外部 API 时将发送必要的数据内容（有费用与隐私风险）</div>
            </a-form-item>
            <a-form-item>
              <a-button type="primary" @click="saveSettings">保存设置</a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <!-- 分析与字典 -->
        <a-tab-pane key="dict" tab="分析与字典">
          <a-form layout="vertical">
            <a-form-item label="停用词表设置">
              <a-checkbox v-model:checked="settings.useDefaultStopwords">使用默认哈工大停用词表</a-checkbox>
            </a-form-item>
            <a-form-item label="自定义停用词 (每行一个)">
              <a-textarea 
                v-model:value="settings.customStopwords" 
                :rows="6" 
                placeholder="输入自定义停用词，按回车分隔" 
              />
            </a-form-item>
            <a-form-item>
              <a-button type="primary" @click="saveSettings">保存设置</a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <!-- 图表与展示 -->
        <a-tab-pane key="chart" tab="图表与展示">
          <a-form layout="vertical">
            <a-form-item label="默认图表主题色卡">
              <a-select v-model:value="settings.chartTheme" style="width: 200px">
                <a-select-option value="macaron">低饱和马卡龙</a-select-option>
                <a-select-option value="warm">柔和唯美 (暖色)</a-select-option>
                <a-select-option value="cold">柔和唯美 (冷色)</a-select-option>
                <a-select-option value="simple">简约朴素</a-select-option>
                <a-select-option value="morandi">莫兰迪</a-select-option>
                <a-select-option value="business">黑金商务</a-select-option>
                <a-select-option value="high-contrast">高对比</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item>
              <a-button type="primary" @click="saveSettings">保存设置</a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>

        <!-- 导出与性能 -->
        <a-tab-pane key="export" tab="导出与性能">
          <a-form layout="vertical">
            <a-form-item label="默认导出参数">
              <a-space direction="vertical">
                <a-checkbox v-model:checked="settings.exportTransparentBg">PNG 导出透明背景</a-checkbox>
                <div>
                  PNG 导出倍率：
                  <a-input-number v-model:value="settings.exportPngScale" :min="1" :max="5" />
                </div>
              </a-space>
            </a-form-item>
            <a-form-item label="性能策略">
              <a-space direction="vertical">
                <div>
                  表格默认分页大小：
                  <a-input-number v-model:value="settings.pageSize" :min="10" :max="1000" />
                </div>
                <div>
                  直方图默认聚合桶数：
                  <a-input-number v-model:value="settings.histogramBins" :min="10" :max="200" />
                </div>
              </a-space>
            </a-form-item>
            <a-form-item>
              <a-button type="primary" @click="saveSettings">保存设置</a-button>
            </a-form-item>
          </a-form>
        </a-tab-pane>
      </a-tabs>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { message } from 'ant-design-vue';

const activeTab = ref('api');

const settings = ref({
  deepseekApiKey: '',
  allowDataExport: false,
  useDefaultStopwords: true,
  customStopwords: '',
  chartTheme: 'macaron',
  exportTransparentBg: false,
  exportPngScale: 2,
  pageSize: 50,
  histogramBins: 50
});

const saveSettings = () => {
  // TODO: Save settings via API or local storage
  message.success('设置已保存并生效');
};
</script>

<style scoped>
.settings-container {
  height: 100%;
}
.h-full {
  height: 100%;
}
.form-hint {
  font-size: 12px;
  color: var(--text-secondary);
  margin-top: 4px;
}
.warning-hint {
  color: var(--warning-color, #faad14);
}
</style>
