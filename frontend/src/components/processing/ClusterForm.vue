<template>
  <div>
    <a-form-item label="聚类算法">
      <a-select v-model:value="form.algorithm">
        <a-select-option value="kmeans">K-Means</a-select-option>
        <a-select-option value="dbscan">DBSCAN</a-select-option>
        <a-select-option value="hdbscan">HDBSCAN</a-select-option>
        <a-select-option value="meanshift">MeanShift</a-select-option>
      </a-select>
    </a-form-item>
    <a-form-item label="特征列">
      <a-select v-model:value="form.features" mode="multiple" placeholder="选择数值特征列">
        <a-select-option v-for="column in numericColumns" :key="column" :value="column">
          {{ column }}
        </a-select-option>
      </a-select>
    </a-form-item>

    <template v-if="form.algorithm === 'kmeans'">
      <a-form-item>
        <a-checkbox v-model:checked="form.auto_k">自动寻找最佳 K 值</a-checkbox>
      </a-form-item>
      <template v-if="form.auto_k">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="最小 K">
              <a-input-number v-model:value="form.k_min" :min="2" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="最大 K">
              <a-input-number v-model:value="form.k_max" :min="3" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
      </template>
      <a-form-item v-else label="K 值">
        <a-input-number v-model:value="form.k" :min="2" :max="20" style="width: 100%" />
      </a-form-item>
    </template>

    <template v-if="form.algorithm === 'dbscan'">
      <a-row :gutter="12">
        <a-col :span="12">
          <a-form-item label="eps">
            <a-input-number v-model:value="form.eps" :min="0.1" :step="0.1" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="min_samples">
            <a-input-number v-model:value="form.min_samples" :min="1" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>
    </template>

    <template v-if="form.algorithm === 'hdbscan'">
      <a-form-item label="min_cluster_size">
        <a-input-number v-model:value="form.min_cluster_size" :min="2" style="width: 100%" />
      </a-form-item>
    </template>

    <template v-if="form.algorithm === 'meanshift'">
      <a-form-item label="bandwidth">
        <a-input-number v-model:value="form.bandwidth" :min="0" :step="0.1" style="width: 100%" />
      </a-form-item>
    </template>

    <a-button type="primary" block :loading="processing" @click="$emit('run')">运行聚类</a-button>
  </div>
</template>

<script setup lang="ts">
export interface ClusterFormState {
  algorithm: 'kmeans' | 'dbscan' | 'hdbscan' | 'meanshift'
  features: string[]
  auto_k: boolean
  k: number
  k_min: number
  k_max: number
  eps: number
  min_samples: number
  min_cluster_size: number
  bandwidth: number | undefined
}

defineProps<{
  form: ClusterFormState
  numericColumns: string[]
  processing: boolean
}>()

defineEmits<{ (event: 'run'): void }>()
</script>
