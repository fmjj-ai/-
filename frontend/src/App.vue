<template>
  <a-config-provider :theme="themeConfig" :locale="zhCN">
    <!-- 视觉层：固定全屏，位于内容下方 -->
    <InkBackdrop />
    <ParticleField />
    <!-- 业务层 -->
    <router-view />
  </a-config-provider>
</template>

<script setup lang="ts">
import { reactive } from 'vue';
import zhCN from 'ant-design-vue/es/locale/zh_CN';
import InkBackdrop from '@/components/effects/InkBackdrop.vue';
import ParticleField from '@/components/effects/ParticleField.vue';

/* 主题令牌：与 variables.css 中的色板保持一致 */
const themeConfig = reactive({
  token: {
    colorPrimary: '#5a7a8c',          /* 远山黛 */
    colorSuccess: '#6fa287',          /* 青瓷 */
    colorWarning: '#c69a4a',          /* 琥珀 */
    colorError:   '#c75450',          /* 朱砂 */
    colorInfo:    '#7c97b8',          /* 烟青 */
    colorTextBase:      '#2d3239',
    colorTextSecondary: '#4a5260',
    colorBgBase:      '#f7f3ec',
    colorBgContainer: 'rgba(255, 253, 248, 0.86)',
    colorBgElevated:  'rgba(255, 253, 248, 0.92)',
    colorBorder:        'rgba(74, 82, 96, 0.18)',
    colorBorderSecondary: 'rgba(74, 82, 96, 0.10)',
    borderRadius: 12,
    borderRadiusLG: 16,
    borderRadiusSM: 8,
    fontFamily: "'HarmonyOS Sans SC', 'PingFang SC', 'Microsoft YaHei', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    motionDurationMid: '0.3s',
    motionDurationSlow: '0.45s',
    wireframe: false,
  },
  components: {
    Card:   { boxShadowTertiary: 'none' },
    Button: { primaryShadow: 'none', defaultShadow: 'none' },
    Layout: { headerBg: 'transparent', siderBg: 'transparent', bodyBg: 'transparent' },
    Menu:   { itemBg: 'transparent', subMenuItemBg: 'transparent' },
  },
});
</script>

<style>
/* 全局样式（含设计令牌、ant 组件柔化覆写）入口 */
@import '@/style.css';
</style>
