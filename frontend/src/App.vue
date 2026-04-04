<template>
  <a-config-provider :theme="themeConfig">
    <router-view />
  </a-config-provider>
</template>

<script setup lang="ts">
import { reactive } from 'vue';

const themeConfig = reactive({
  token: {
    colorPrimary: '#7c97b8',
    colorSuccess: '#6fa287',
    colorWarning: '#d3a35f',
    colorError: '#c97878',
    colorInfo: '#7c97b8',
    colorTextBase: '#1f2430',
    colorTextSecondary: '#5b6475',
    colorBgBase: '#f6f7fb',
    colorBgContainer: '#f9fafd',
    colorBgElevated: '#ffffff',
    colorBorder: '#dfe4ee',
    borderRadius: 14,
    fontFamily: "'HarmonyOS Sans SC', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif, 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', 'Noto Color Emoji'",
  }
});
</script>

<style>
/* Global styles can be placed here or in variables.css */
@import '@/assets/styles/variables.css';
</style>
