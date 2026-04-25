<template>
  <div>
    <a-alert
      v-if="secondPassSummary"
      type="info"
      show-icon
      class="mb-16"
      :message="secondPassMessage"
    />
    <a-alert
      v-for="warning in warnings"
      :key="warning"
      type="warning"
      show-icon
      class="mb-12"
      :message="warning"
    />
    <a-empty v-if="!warnings.length && !secondPassSummary" description="当前没有额外提示" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  warnings: string[]
  secondPassSummary: any | null
}>()

const secondPassMessage = computed(() => {
  const summary = props.secondPassSummary
  if (!summary) return ''
  const parts = [
    `高置信度正向样本 ${summary.pseudo_positive_count || 0} 条`,
    `高置信度负向样本 ${summary.pseudo_negative_count || 0} 条`,
  ]
  if (summary.trained) {
    return `已完成二次 SnowNLP 训练，${parts.join('，')}`
  }
  if (summary.warning) {
    return `${summary.warning}；${parts.join('，')}`
  }
  return parts.join('，')
})
</script>

<style scoped>
.mb-12 {
  margin-bottom: 12px;
}
.mb-16 {
  margin-bottom: 16px;
}
</style>
