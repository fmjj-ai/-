<template>
  <div>
    <a-form-item label="目标列">
      <a-select v-model:value="form.column" placeholder="选择需要编码的列">
        <a-select-option v-for="column in columns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item label="多值分隔符">
      <a-input v-model:value="form.separator" placeholder="默认为 ," />
    </a-form-item>
    <a-form-item>
      <a-checkbox v-model:checked="form.keep_original">保留原始列</a-checkbox>
    </a-form-item>
    <a-button type="primary" block :loading="processing" @click="$emit('preview')">预览并应用编码</a-button>
  </div>
</template>

<script setup lang="ts">
export interface EncodingFormState {
  column: string
  separator: string
  keep_original: boolean
}

defineProps<{
  form: EncodingFormState
  columns: string[]
  processing: boolean
}>()

defineEmits<{ (event: 'preview'): void }>()
</script>
