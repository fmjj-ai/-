<template>
  <div class="home">
    <a-card title="首页概览" :bordered="false" class="neumorphism-card">
      <p>欢迎来到数据分析工作台。</p>
      <a-button type="primary" @click="$router.push({ name: 'Projects' })">查看项目</a-button>
    </a-card>
  </div>
</template>

<script setup lang="ts">
// Home page
</script>

<style scoped>
.neumorphism-card {
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-outer);
  background: var(--bg-elevated);
}
</style>
