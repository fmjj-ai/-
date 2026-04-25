<template>
  <div v-if="artifacts.length" class="wordcloud-grid">
    <a-card v-for="artifact in artifacts" :key="artifact.id" :title="artifact.name" size="small">
      <img :src="buildArtifactPreviewUrl(artifact.id)" :alt="artifact.name" class="wordcloud-image" />
    </a-card>
  </div>
  <a-empty v-else description="暂无词云产物" />
</template>

<script setup lang="ts">
defineProps<{
  artifacts: any[]
  buildArtifactPreviewUrl: (id: number) => string
}>()
</script>

<style scoped>
.wordcloud-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.wordcloud-image {
  width: 100%;
  border-radius: 10px;
  background: #fff;
}
</style>
